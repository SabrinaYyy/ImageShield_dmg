"""Offline, single-image protection service used by the desktop UI."""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageOps
from torchvision import transforms

from .resources import resource_path

ProgressCallback = Callable[[float, str], None]
CancelCallback = Callable[[], bool]


class ProtectionCancelled(RuntimeError):
    """Raised when the user stops an active protection job."""


@dataclass(frozen=True)
class ProtectionSettings:
    resolution: int = 512
    eps: float = 0.05
    alpha: float = 1 / 255
    steps: int = 100
    seed: int = 33
    eot_weight: float = 0.1
    eot_kernel: int = 5
    eot_sigma: float = 1.5

    def validate(self) -> None:
        if self.resolution < 64:
            raise ValueError("Resolution must be at least 64 pixels.")
        if self.steps < 1:
            raise ValueError("Protection steps must be at least 1.")
        if not 0 < self.eps <= 1:
            raise ValueError("Epsilon must be between 0 and 1.")
        if self.alpha <= 0:
            raise ValueError("Alpha must be positive.")
        if self.eot_kernel < 1 or self.eot_kernel % 2 == 0:
            raise ValueError("The EOT kernel must be a positive odd number.")
        if self.eot_sigma <= 0:
            raise ValueError("The EOT sigma must be positive.")


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


def apply_gaussian_smoothing(
    image: torch.Tensor,
    kernel_size: int,
    sigma: float,
) -> torch.Tensor:
    coordinates = (
        torch.arange(kernel_size, dtype=torch.float32, device=image.device)
        - kernel_size // 2
    )
    gaussian = torch.exp(-(coordinates**2) / (2 * sigma**2))
    gaussian = gaussian / gaussian.sum()
    kernel = gaussian.outer(gaussian).unsqueeze(0).unsqueeze(0)
    kernel = kernel.to(image.device, image.dtype)
    padding = kernel_size // 2
    channels = [
        F.conv2d(image[:, index : index + 1], kernel, padding=padding)
        for index in range(image.shape[1])
    ]
    return torch.cat(channels, dim=1)


def get_embedding(
    image: torch.Tensor,
    vae,
    scheduler,
    device: torch.device,
    dtype: torch.dtype,
    fixed_noise: torch.Tensor,
    fixed_timesteps: torch.Tensor,
) -> torch.Tensor:
    image = image.to(device, dtype=dtype)
    latent_mean = vae.encode(image).latent_dist.mean
    latents = latent_mean * vae.config.scaling_factor
    noisy_latents = scheduler.add_noise(latents, fixed_noise, fixed_timesteps)
    return torch.cat([noisy_latents, latent_mean], dim=1)


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
    generator = torch.Generator(device="cpu")
    generator.manual_seed(image_seed)

    with torch.no_grad():
        reference_latent = (
            vae.encode(original).latent_dist.mean * vae.config.scaling_factor
        )

    fixed_noise = torch.randn(reference_latent.shape, generator=generator).to(
        device, dtype=dtype
    )
    fixed_timesteps = torch.randint(
        0,
        scheduler.config.num_train_timesteps,
        (reference_latent.shape[0],),
        generator=generator,
    ).to(device)
    initial_delta = (
        torch.rand(original.shape, generator=generator) * 2.0 - 1.0
    ) * (settings.eps * 0.5)
    initial_delta = initial_delta.to(device, dtype=dtype)

    with torch.no_grad():
        target_embedding = get_embedding(
            original,
            vae,
            scheduler,
            device,
            dtype,
            fixed_noise,
            fixed_timesteps,
        ).detach()
        gaussian_reference = apply_gaussian_smoothing(
            original,
            settings.eot_kernel,
            settings.eot_sigma,
        ).detach()

    protected = torch.clamp(original + initial_delta, 0.0, 1.0).detach()

    for step in range(settings.steps):
        if cancelled and cancelled():
            raise ProtectionCancelled("Protection stopped by the user.")

        protected.requires_grad_(True)
        embedding = get_embedding(
            protected,
            vae,
            scheduler,
            device,
            dtype,
            fixed_noise,
            fixed_timesteps,
        )
        latent_loss = -F.mse_loss(embedding.float(), target_embedding.float())
        eot_loss = (
            F.mse_loss(
                apply_gaussian_smoothing(
                    protected,
                    settings.eot_kernel,
                    settings.eot_sigma,
                ),
                gaussian_reference,
            )
            if settings.eot_weight > 0
            else torch.zeros((), device=device)
        )
        (latent_loss + settings.eot_weight * eot_loss).backward()

        with torch.no_grad():
            protected = protected - settings.alpha * protected.grad.sign()
            delta = torch.clamp(
                protected - original,
                -settings.eps,
                settings.eps,
            )
            protected = torch.clamp(original + delta, 0.0, 1.0).detach()

        if progress:
            progress((step + 1) / settings.steps, f"Protection step {step + 1}/{settings.steps}")

    if cancelled and cancelled():
        raise ProtectionCancelled("Protection stopped by the user.")

    return protected.cpu()


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
        return tensor_to_pil(protected)

    def cancel(self) -> None:
        self._cancel_event.set()
