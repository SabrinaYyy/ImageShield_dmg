# GitHub Setup Guide

## For Users (DMG Download)

Users will:
1. Download `ImageShield.dmg` from GitHub Releases
2. Drag ImageShield.app to Applications
3. Launch the app — **everything works with one click** ✅
   - Models are bundled in the DMG
   - No installation needed
   - No terminal commands

---

## For Teammates (GitHub Development)

### Initial Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/ImageShield.git
cd ImageShield

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt  # For building DMG/exe

# 4. First run — models auto-download (5-10 mins on first launch)
python app.py
```

### What Happens on First Run

When a teammate runs `python app.py`:
- ✅ Models automatically download from Hugging Face (~5-10 GB)
- ✅ Downloaded to platform-specific cache:
  - **macOS**: `~/Library/Application Support/ImageShield/models/`
  - **Windows**: `%LOCALAPPDATA%\ImageShield\models\`
  - **Linux**: `~/.local/share/ImageShield/models/`
- ✅ Cached for future runs
- ✅ App is ready to use

### Development Workflow

```bash
# Activate environment
source .venv/bin/activate

# Run the app
python app.py

# Run tests
pytest

# Build DMG for distribution
./scripts/build_macos.sh  # Creates: dist/dmg/ImageShield.dmg
```

---

## Publishing to GitHub

### Terminal Commands to Execute

```bash
# Initialize git repository (if not already done)
git init

# Add all files (respects .gitignore)
git add .

# Verify models/ and build/ are excluded
git status  # Should NOT show models/ or dist/ folders

# Create initial commit
git commit -m "Initial commit: ImageShield image protection tool"

# Add remote repository
git remote add origin https://github.com/YOUR_USERNAME/ImageShield.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Create GitHub Release with DMG

```bash
# Build the DMG locally
./scripts/build_macos.sh

# Install GitHub CLI (if not already installed)
brew install gh

# Create a release and upload DMG
gh release create v1.0.0 \
  ./dist/dmg/ImageShield.dmg \
  --title "ImageShield v1.0.0" \
  --notes "Initial release: Image protection with offline models"

# Or manually upload via GitHub web interface:
# 1. Go to your repo → Releases → Draft a new release
# 2. Tag: v1.0.0
# 3. Upload ImageShield.dmg file
# 4. Publish
```

---

## File Exclusions Explained

### ❌ NOT uploaded to GitHub (in .gitignore):
- `models/` — Large ML models (10GB+) — auto-downloaded on first run
- `build/` — Build artifacts
- `dist/` — Distribution files
- `__pycache__/` — Python cache
- `.venv/` — Virtual environment
- `.env` — Local configuration (use `.env.example` instead)

### ✅ Uploaded to GitHub:
- `imageshield/` — Source code
- `app.py` — Main entry point
- `tests/` — Test suite
- `scripts/` — Build scripts
- `packaging/` — Packaging configs
- `requirements.txt` — Dependencies
- `.env.example` — Configuration template
- `README.md` — Documentation

---

## Environment Variables

For teammates working on the code:

```bash
# Create .env from template (optional)
cp .env.example .env

# Edit .env if needed, but DON'T commit it
nano .env
```

Available variables:
- `IMAGESHIELD_DATA_DIR` — Override where user data is stored
- `IMAGESHIELD_SMOKE_TEST` — Used by build scripts (don't change)

---

## Troubleshooting

### Models not downloading?
```bash
# Check internet connection and try again
python app.py

# Or manually trigger download
python -c "from imageshield.model_manager import ensure_models_downloaded; ensure_models_downloaded()"
```

### Build fails?
```bash
# Clean old builds
rm -rf build/ dist/

# Rebuild
./scripts/build_macos.sh
```

### Old cache issues?
```bash
# Clear model cache
rm -rf ~/.imageshield-cache/

# Redownload on next run
python app.py
```

---

## Next Steps

1. ✅ Set up repo: Follow "Publishing to GitHub" section above
2. ✅ Create GitHub Release with DMG
3. ✅ Share release link with users
4. ✅ Share repo link with teammates for development
