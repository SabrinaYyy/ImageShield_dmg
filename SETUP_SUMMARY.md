# ImageShield GitHub & Distribution Setup - Complete Summary

## What I've Set Up For You

✅ **Model Auto-Download System** — Models download on first run for teammates
✅ **DMG Bundling** — Users get everything in one click
✅ **GitHub-Ready** — Lean repo with only source code

---

## 📦 Two Distribution Paths

### Path 1: Users (DMG Download) — ONE CLICK
```
User downloads ImageShield.dmg from GitHub Releases
  ↓
Drag to Applications
  ↓
Click to launch
  ↓
Everything works (models included in DMG)
```

### Path 2: Teammates (GitHub Source) — DEVELOPMENT
```
Teammate clones from GitHub
  ↓
Run: python app.py
  ↓
Models auto-download on first run (~5-10 mins)
  ↓
Ready to develop/test
```

---

## 🚀 Terminal Commands - Step by Step

### FIRST TIME SETUP (One Time)

```bash
# 1. Configure git (if not done)
git config --global user.name "Your Name"
git config --global user.email "your.email@github.com"

# 2. From your ImageShield directory
cd /Users/sabrinay./Desktop/ImageShield

# 3. Initialize git
git init

# 4. Add all files (models/ automatically excluded by .gitignore)
git add .

# 5. Check what will be uploaded
git status

# 6. Create first commit
git commit -m "Initial commit: ImageShield image protection tool"

# 7. Add GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/ImageShield.git

# 8. Push to GitHub
git branch -M main
git push -u origin main
```

### BUILD & RELEASE DMG (Every Release)

```bash
# Build the DMG
./scripts/build_macos.sh

# Creates: /Desktop/ImageShield/dist/dmg/ImageShield.dmg

# Option A: Upload via CLI (requires GitHub CLI)
brew install gh  # One-time
gh release create v1.0.0 \
  ./dist/dmg/ImageShield.dmg \
  --title "ImageShield v1.0.0" \
  --notes "First release: Image protection tool"

# Option B: Upload via GitHub.com (no CLI needed)
# 1. Go to: https://github.com/YOUR_USERNAME/ImageShield/releases
# 2. Click "Draft a new release"
# 3. Tag: v1.0.0
# 4. Drag dist/dmg/ImageShield.dmg to the upload area
# 5. Click "Publish release"
```

---

## 📁 What Gets Uploaded vs. Excluded

### ✅ Uploaded to GitHub (14 MB):
```
app.py
requirements.txt
requirements-build.txt
.env.example
.gitignore
README.md
imageshield/
├── __init__.py
├── protection.py
├── resources.py
├── ui.py
└── model_manager.py (NEW - handles auto-download)
scripts/
tests/
packaging/
licenses/
pyproject.toml
```

### ❌ NOT Uploaded (Excluded):
```
models/               # 10GB+ - bundled in DMG for users, auto-downloaded for teammates
build/               # Build artifacts
dist/                # Distribution files
__pycache__/         # Python cache
.venv/               # Virtual environment
.env                 # Local config (use .env.example instead)
.pytest_cache/
```

---

## 🔧 What Changed in Your Project

### New Files Created:
1. **imageshield/model_manager.py** — Handles model auto-download
2. **.env.example** — Template for environment variables
3. **GITHUB_SETUP.md** — This detailed guide
4. **TERMINAL_COMMANDS.sh** — Quick copy-paste commands

### Modified Files:
1. **.gitignore** — Added `models/`, `.env`, `.env.local`
2. **imageshield/protection.py** — Now uses model manager for auto-download
3. **requirements.txt** — Added `huggingface-hub` package

---

## 👥 For Teammates

When teammates clone your GitHub repo:

```bash
# They run this
git clone https://github.com/YOUR_USERNAME/ImageShield.git
cd ImageShield

# Set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# First run (models auto-download to their machine)
python app.py

# Models cached at:
# macOS: ~/Library/Application Support/ImageShield/models/
# Windows: %LOCALAPPDATA%\ImageShield\models\
# Linux: ~/.local/share/ImageShield/models/
```

---

## 💾 For Users

Users never see the GitHub repo. They:

1. Visit GitHub Releases page
2. Download `ImageShield.dmg` (latest version)
3. Drag to Applications
4. Click to run
5. Everything works instantly (models bundled in DMG)

---

## ⚙️ Environment Variables

For teammates (optional):
```bash
# Create .env from template
cp .env.example .env

# Available variables:
# IMAGESHIELD_DATA_DIR=custom/path  # Override output directory
```

**Never commit .env** — it's in .gitignore

---

## 🔍 Quick Verification Checklist

Before publishing to GitHub:

```bash
# 1. Verify models are excluded
git status | grep -i models  # Should return nothing

# 2. Verify build artifacts excluded
git status | grep -i build   # Should return nothing
git status | grep -i dist    # Should return nothing

# 3. Check what will be committed
git log --stat

# 4. Count files being uploaded
git ls-files | wc -l  # Should be ~20-30 files, not 10GB+
```

---

## 🚨 Common Issues & Fixes

### Issue: Models getting committed to git
```bash
# Solution: Remove from git tracking (don't delete from disk)
git rm -r --cached models/
git commit -m "Remove models from git tracking"
```

### Issue: Teammates getting "models not found"
```bash
# Models auto-download on first run
# If stuck, manually trigger:
python -c "from imageshield.model_manager import ensure_models_downloaded; ensure_models_downloaded()"
```

### Issue: DMG file missing models
```bash
# Models SHOULD be bundled in DMG by PyInstaller
# If not, check build_macos.sh includes models in spec file
```

---

## 📝 Next Actions

1. **Run git setup commands** (Terminal Commands - Step by Step section)
2. **Push to GitHub** 
3. **Build DMG** (`./scripts/build_macos.sh`)
4. **Create Release** (upload DMG to GitHub Releases)
5. **Share links**:
   - Users: Release DMG download link
   - Teammates: GitHub repo link

---

## 📚 Reference Files

- `GITHUB_SETUP.md` — Detailed setup guide
- `TERMINAL_COMMANDS.sh` — Copy-paste terminal commands
- `.env.example` — Configuration template
- `.gitignore` — What's excluded from git
- `imageshield/model_manager.py` — Model downloading logic

---

Questions? Check [GITHUB_SETUP.md](GITHUB_SETUP.md) for more details.
