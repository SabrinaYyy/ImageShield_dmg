"""Offline, single-image protection service used by the desktop UI."""

from __future__ import annotations

import hashlib
import gc
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageOps
from torchvision import transforms
import torchvision.transforms.functional as TF

from .resources import resource_path

ProgressCallback = Callable[[float, str], None]
CancelCallback = Callable[[], bool]


class ProtectionCancelled(RuntimeError):
    """Raised when the user stops an active protection job."""


@dataclass(frozen=True)
class ProtectionSettings:
    resolution: int = 512
    eps: float = 4/255
    alpha: float = 1 / 255
    steps: int = 100
    seed: int = 33
    beta: float = 0.2        # perceptual consistency loss weight
    eot_angle: float = 5.0   # rotation angle in degrees for EOT-R

    def validate(self) -> None:
        if self.resolution < 64:
            raise ValueError("Resolution must be at least 64 pixels.")
        if self.steps < 1:
            raise ValueError("Protection steps must be at least 1.")
        if not 0 < self.eps <= 1:
            raise ValueError("Epsilon must be between 0 and 1.")
        if self.alpha <= 0:
            raise ValueError("Alpha must be positive.")
        if self.beta < 0:
            raise ValueError("Beta must be non-negative.")


def select_device() -> tuple[torch.device, torch.dtype]:
    if torch.backends.mps.is_available():
        return torch.device("mps"), torch.float32
    if torch.cuda.is_available():
        return torch.device("cuda"), torch.float32
    return torch.device("cpu"), torch.float32


def device_summary(device: torch.device) -> str:
    if device.type == "mps":
        return "Apple GPU acceleration (Metal/MPS)"
    if device.type == "cuda":
        name = torch.cuda.get_device_name(device)
        memory_gb = torch.cuda.get_device_properties(device).total_memory / (1024**3)
        return f"{name} ({memory_gb:.1f} GB VRAM)"
    return "CPU mode (protection will be considerably slower)"


def make_preprocess(resolution: int):
    return transforms.Compose(
        [
            transforms.Resize(
                resolution,
                interpolation=transforms.InterpolationMode.BILINEAR,
            ),
            transforms.CenterCrop(resolution),
            transforms.ToTensor(),
        ]
    )


def get_emb(
    image: torch.Tensor,
    vae,
    scheduler,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    """Stochastic VAE embedding — matches notebook get_emb() exactly."""
    image = image.to(device, dtype=dtype)
    latents = vae.encode(image).latent_dist.sample() * vae.config.scaling_factor
    noise = torch.randn_like(latents)
    bsz = latents.shape[0]
    timesteps = torch.randint(
        0, scheduler.config.num_train_timesteps, (bsz,), device=device
    ).long()
    noisy_latents = scheduler.add_noise(latents, noise, timesteps)
    original_image_embeds = vae.encode(image).latent_dist.sample()
    return torch.cat([noisy_latents, original_image_embeds], dim=1)


def rotate_batch(x: torch.Tensor, angle: float) -> torch.Tensor:
    """Rotate each image in the batch — differentiable.

    grid_sampler_2d_backward is not yet implemented for MPS, so we perform the
    rotation on CPU and transfer back.  Device transfers are differentiable,
    so gradients flow through the round-trip correctly.
    """
    target_device = x.device
    if target_device.type == "mps":
        x = x.cpu()
    rotated = torch.stack(
        [
            TF.rotate(x[i], angle, interpolation=transforms.InterpolationMode.BILINEAR)
            for i in range(x.shape[0])
        ]
    )
    return rotated.to(target_device)


def derive_image_seed(base_seed: int, image: Image.Image) -> int:
    digest = hashlib.sha256()
    digest.update(str(base_seed).encode("ascii"))
    digest.update(image.tobytes())
    return int.from_bytes(digest.digest()[:4], "big")


def pgd_protect(
    original: torch.Tensor,
    vae,
    scheduler,
    device: torch.device,
    dtype: torch.dtype,
    settings: ProtectionSettings,
    image_seed: int,
    progress: ProgressCallback | None = None,
    cancelled: CancelCallback | None = None,
) -> torch.Tensor:
    original = original.to(device, dtype=dtype)

    # Seed globally so init delta + stochastic get_emb calls are reproducible
    torch.manual_seed(image_seed)

    # Target embedding: unrotated original, computed once before the loop
    with torch.no_grad():
        tgt_emb = get_emb(original, vae, scheduler, device, dtype).detach()

    # Random L∞ init — full budget, matching notebook
    delta = (torch.rand(original.shape) * 2.0 - 1.0) * settings.eps
    delta = delta.to(device, dtype=dtype)
    delta = torch.clamp(delta, -settings.eps, settings.eps)
    clipped = torch.clamp(original + delta, 0.0, 1.0)
    delta = (clipped - original).detach()

    for step in range(settings.steps):
        if cancelled and cancelled():
            raise ProtectionCancelled("Protection stopped by the user.")

        perturbed = torch.clamp(original + delta, 0.0, 1.0).detach().requires_grad_(True)

        # EOT-R: rotation applied inside the embedding loss only
        rotated = rotate_batch(perturbed, settings.eot_angle)
        img_emb = get_emb(rotated, vae, scheduler, device, dtype)

        real_mse = F.mse_loss(img_emb.float(), tgt_emb.float())
        loss_percep = settings.beta * F.mse_loss(perturbed, original)
        total_loss = -real_mse + loss_percep
        total_loss.backward()

        with torch.no_grad():
            delta = delta - settings.alpha * perturbed.grad.sign()
            delta = torch.clamp(delta, -settings.eps, settings.eps)
            clipped = torch.clamp(original + delta, 0.0, 1.0)
            delta = (clipped - original).detach()

        if progress:
            progress(
                (step + 1) / settings.steps,
                f"Protection step {step + 1}/{settings.steps}",
            )

    if cancelled and cancelled():
        raise ProtectionCancelled("Protection stopped by the user.")

    return torch.clamp(original + delta, 0.0, 1.0).cpu()


def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    array = tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    return Image.fromarray((np.clip(array, 0, 1) * 255).astype(np.uint8))


class ProtectionService:
    """Lazily load bundled weights once and serialize protection jobs."""

    def __init__(
        self,
        model_dir: Path | None = None,
        settings: ProtectionSettings | None = None,
    ) -> None:
        self.model_dir = model_dir or resource_path("models", "instruct-pix2pix")
        self.settings = settings or ProtectionSettings()
        self.settings.validate()
        self.device, self.dtype = select_device()
        self._vae = None
        self._scheduler = None
        self._load_lock = threading.Lock()
        self._protection_lock = threading.Lock()
        self._cancel_event = threading.Event()

    @property
    def is_loaded(self) -> bool:
        return self._vae is not None and self._scheduler is not None

    def validate_model_files(self) -> None:
        required = (
            self.model_dir / "vae" / "config.json",
            self.model_dir / "vae" / "diffusion_pytorch_model.safetensors",
            self.model_dir / "scheduler" / "scheduler_config.json",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "The offline model bundle is incomplete. Missing: " + ", ".join(missing)
            )

    def load(self) -> None:
        if self.is_loaded:
            return
        with self._load_lock:
            if self.is_loaded:
                return
            self.validate_model_files()
            from diffusers.models.autoencoders.autoencoder_kl import AutoencoderKL
            from diffusers.schedulers.scheduling_ddpm import DDPMScheduler

            vae = AutoencoderKL.from_pretrained(
                self.model_dir / "vae",
                local_files_only=True,
            ).to(self.device, dtype=self.dtype)
            vae.requires_grad_(False)
            vae.eval()
            scheduler = DDPMScheduler.from_pretrained(
                self.model_dir / "scheduler",
                local_files_only=True,
            )
            self._vae = vae
            self._scheduler = scheduler

    def protect(
        self,
        image: Image.Image,
        settings: ProtectionSettings | None = None,
        progress: ProgressCallback | None = None,
    ) -> Image.Image:
        if image is None:
            raise ValueError("Please upload an image before starting protection.")
        self.load()

        run_settings = settings or self.settings
        run_settings.validate()
        source = ImageOps.exif_transpose(image).convert("RGB")
        original = make_preprocess(run_settings.resolution)(source).unsqueeze(0)
        image_seed = derive_image_seed(run_settings.seed, source)

        with self._protection_lock:
            self._cancel_event.clear()
            try:
                protected = pgd_protect(
                    original,
                    self._vae,
                    self._scheduler,
                    self.device,
                    self.dtype,
                    run_settings,
                    image_seed,
                    progress,
                    self._cancel_event.is_set,
                )
            finally:
                if self.device.type == "mps" and hasattr(torch, "mps"):
                    torch.mps.empty_cache()
                gc.collect()
        return tensor_to_pil(protected)

    def cancel(self) -> None:
        self._cancel_event.set()
