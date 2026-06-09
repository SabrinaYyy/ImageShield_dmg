# ImageShield Desktop

ImageShield is a self-contained, offline desktop build of the local EditShield
VAE protection prototype. End users install the application, launch it from an
icon, upload an image, and download a protected PNG. They do not need Python,
Conda, a terminal, an account, or an internet connection.

This folder is intentionally independent from the research scripts in its
parent directory.

## Included Components

```text
ImageShield/
  app.py                         desktop entry point
  imageshield/
    protection.py                offline model and PGD service
    resources.py                 source/bundle/user-data paths
    ui.py                        Gradio interface
  models/instruct-pix2pix/
    vae/                         bundled VAE configuration and weights
    scheduler/                   bundled scheduler configuration
  ImageShield.spec               PyInstaller build definition
  packaging/
    macos/                       signing entitlements
    windows/                     Inno Setup installer definition
  scripts/                       validation and platform build scripts
  tests/                         tests that do not load the real checkpoint
```

The bundled model files are loaded with `local_files_only=True`. The application
does not fall back to downloading weights.

## Development

Use Python 3.10 in a dedicated environment:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python scripts/validate_bundle.py
pytest
python app.py
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

The Gradio server binds only to `127.0.0.1`, sharing is disabled, and uploaded
images are processed locally. Generated downloads are stored under the user's
application-data directory and files older than 24 hours are removed at the
next launch.

The main screen provides:

- Resolution choices of 128, 256, or 512 pixels.
- An optimization-step slider from 20 to 100 in increments of 10.
- A Stop button that requests cancellation between optimization steps.

The default is 256 pixels and 20 steps for a more practical desktop runtime.
Stopping is cooperative: the current VAE operation must finish before the job
can exit, so the response is not always instantaneous. If the application does
not respond, quit ImageShield from the Dock or use macOS Force Quit.

Developers and automated tests can override that location with the
`IMAGESHIELD_DATA_DIR` environment variable. Set `IMAGESHIELD_OPEN_BROWSER=0`
to start the local server without opening a browser. Set
`IMAGESHIELD_SMOKE_TEST=1` to load the bundled model, run a one-step protection
on a generated test image, and exit.

## Build macOS

Build macOS releases on macOS. The current development machine is Apple Silicon,
so its build targets Apple Silicon unless a separate architecture strategy is
configured.

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

Development output:

```text
dist/ImageShield.app
dist/dmg/ImageShield.dmg
```

For a signed build:

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Organization (TEAMID)"
./scripts/build_macos.sh
```

Signing alone is not sufficient for public distribution. Submit the DMG for
Apple notarization and staple the notarization result before release.

## Build Windows

Build Windows releases on a Windows machine. PyInstaller does not cross-compile
the macOS build into a Windows executable.

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
.\scripts\build_windows.ps1
```

This creates:

```text
dist\ImageShield\ImageShield.exe
```

Install Inno Setup, open `packaging\windows\ImageShield.iss`, and compile it to
create `dist\installer\ImageShield-Setup-0.1.0.exe`. Sign both the executable and
installer before public distribution.

## End-User Experience

macOS:

1. Download `ImageShield.dmg`.
2. Open it and drag ImageShield into Applications.
3. Open ImageShield from Applications.
4. The local interface opens in the default browser.

Windows:

1. Download `ImageShield-Setup-0.1.0.exe`.
2. Follow the installer.
3. Open ImageShield from the Start menu or desktop shortcut.
4. The local interface opens in the default browser.

Closing the browser tab does not necessarily stop the desktop process. Users can
quit ImageShield from the Dock, Task Manager, or operating-system application
controls.

## Release Checklist

1. Confirm redistribution rights for the model checkpoint and all dependencies.
2. Replace the placeholder notices in `licenses/` with authoritative license
   texts and retain required attributions.
3. Run `python scripts/validate_bundle.py` and `pytest`.
4. Build on a clean machine for each target operating system and architecture.
5. Test without Python installed and with networking disabled.
6. Test model startup, image upload, protection, download, and application exit.
7. Sign and notarize the macOS release.
8. Sign the Windows executable and installer.
9. Publish checksums for every released installer.

## Product Limits

- This implementation is the VAE latent-divergence protection path. It should
  not be described as universal protection against every editing or face-swap
  system.
- Protection returns a center-cropped square PNG at the configured resolution.
- CPU mode is supported but can be considerably slower than MPS or CUDA.
- Only one protection job runs at a time to avoid exhausting accelerator memory.
- Higher resolutions and step counts can take dramatically longer. Runtime
  grows with both image area and the number of optimization steps.
- The final installed size will be much larger than the 319 MB checkpoint
  because it also includes PyTorch, Gradio, and their runtime dependencies.
