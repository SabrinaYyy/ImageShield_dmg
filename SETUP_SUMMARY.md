# ImageShield Setup Summary

## Build Your Own macOS DMG

```bash
git clone https://github.com/SabrinaYyy/ImageShield_dmg.git
cd ImageShield_dmg

python3.10 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

chmod +x scripts/download_model.sh scripts/build_macos.sh
./scripts/download_model.sh
./scripts/build_macos.sh
```

The DMG is created at:

```text
dist/dmg/ImageShield.dmg
```

## What Each Script Does

`scripts/download_model.sh`:

- Downloads the required VAE and scheduler from the original Hugging Face model
  repository.
- Uses the pinned revision
  `31519b5cb02a7fd89b906d88731cd4d6a7bbf88d`.
- Validates that the checkpoint is complete.
- Skips the download when valid files already exist.

`scripts/build_macos.sh`:

- Validates the model files.
- Builds `ImageShield.app` with PyInstaller.
- Runs a packaged protection smoke test.
- Creates `dist/dmg/ImageShield.dmg`.
- Produces an unsigned development build unless
  `APPLE_SIGNING_IDENTITY` is configured.

## Important Clarification

`python app.py` runs ImageShield from source. It does not create a DMG and it
does not auto-download a missing model. Run the download and build scripts shown
above.
