"""Download and manage AI models for offline protection."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable

from .resources import user_data_dir


ProgressCallback = Callable[[float, str], None]


class ModelDownloadError(RuntimeError):
    """Raised when model download fails."""


def get_models_dir() -> Path:
    """
    Get the models directory.
    For bundled apps (DMG), uses bundled models.
    For dev/GitHub, downloads to user data directory.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running from PyInstaller bundle (DMG)
        bundled_models = Path(sys._MEIPASS) / "models" / "instruct-pix2pix"
        if bundled_models.exists():
            return bundled_models
    
    # Development or source installation - use user data dir
    return user_data_dir() / "models" / "instruct-pix2pix"


def ensure_models_downloaded(progress: ProgressCallback | None = None) -> Path:
    """
    Ensure models are available locally. Downloads if needed.
    
    Returns:
        Path to the models directory
        
    Raises:
        ModelDownloadError: If download fails
    """
    models_dir = get_models_dir()
    
    # Check if models already exist
    if _validate_models(models_dir):
        if progress:
            progress(1.0, "Models ready!")
        return models_dir
    
    # Create parent directory
    models_dir.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        _download_models(models_dir, progress)
        
        # Validate after download
        if not _validate_models(models_dir):
            raise ModelDownloadError("Downloaded models are incomplete")
        
        if progress:
            progress(1.0, "Models downloaded successfully!")
        
        return models_dir
        
    except Exception as e:
        raise ModelDownloadError(f"Failed to download models: {e}") from e


def _validate_models(models_dir: Path) -> bool:
    """Check if all required model files exist."""
    required_files = [
        models_dir / "vae" / "config.json",
        models_dir / "vae" / "diffusion_pytorch_model.safetensors",
        models_dir / "scheduler" / "scheduler_config.json",
    ]
    return all(f.is_file() for f in required_files)


def _download_models(models_dir: Path, progress: ProgressCallback | None = None) -> None:
    """
    Download models from Hugging Face.
    
    This uses the diffusers library to cache models in the user data directory.
    """
    try:
        from diffusers.models.autoencoders.autoencoder_kl import AutoencoderKL
        from diffusers.schedulers.scheduling_ddpm import DDPMScheduler
        from huggingface_hub import snapshot_download
    except ImportError as e:
        raise ModelDownloadError(
            "Required packages not installed. Run: pip install -r requirements.txt"
        ) from e
    
    if progress:
        progress(0.1, "Downloading VAE model (this may take 5-10 minutes)...")
    
    try:
        # Download VAE
        vae_dir = models_dir / "vae"
        vae_dir.mkdir(parents=True, exist_ok=True)
        
        snapshot_download(
            "timbrooks/instruct-pix2pix",
            repo_type="model",
            cache_dir=models_dir.parent,
            allow_patterns=["vae/*"],
            local_dir=vae_dir,
            local_dir_use_symlinks=False,
        )
        
        if progress:
            progress(0.6, "Downloading scheduler config...")
        
        # Download scheduler
        scheduler_dir = models_dir / "scheduler"
        scheduler_dir.mkdir(parents=True, exist_ok=True)
        
        snapshot_download(
            "timbrooks/instruct-pix2pix",
            repo_type="model",
            cache_dir=models_dir.parent,
            allow_patterns=["scheduler/*"],
            local_dir=scheduler_dir,
            local_dir_use_symlinks=False,
        )
        
        if progress:
            progress(0.9, "Finalizing models...")
            
    except Exception as e:
        # Clean up partial downloads
        if models_dir.exists():
            import shutil
            shutil.rmtree(models_dir, ignore_errors=True)
        raise ModelDownloadError(f"Model download failed: {e}") from e
