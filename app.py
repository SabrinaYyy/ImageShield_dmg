"""ImageShield desktop entry point."""

import os

from PIL import Image

from imageshield.ui_final import launch


if __name__ == "__main__":
    if os.environ.get("IMAGESHIELD_SMOKE_TEST") == "1":
        from imageshield.protection import ProtectionService, ProtectionSettings

        smoke_service = ProtectionService(
            settings=ProtectionSettings(resolution=64, steps=1)
        )
        smoke_service.protect(Image.new("RGB", (64, 64), color=(128, 128, 128)))
    else:
        launch()
