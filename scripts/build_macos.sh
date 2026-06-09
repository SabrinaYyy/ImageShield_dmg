#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYINSTALLER_CONFIG_DIR="$ROOT/.pyinstaller"

python scripts/validate_bundle.py
python -m PyInstaller --noconfirm --clean ImageShield.spec

APP="$ROOT/dist/ImageShield.app"
if [[ ! -d "$APP" ]]; then
  echo "Build failed: $APP was not created." >&2
  exit 1
fi

IMAGESHIELD_SMOKE_TEST=1 \
IMAGESHIELD_DATA_DIR="$ROOT/.imageshield-smoke" \
"$APP/Contents/MacOS/ImageShield"

if [[ -n "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime \
    --entitlements "$ROOT/packaging/macos/entitlements.plist" \
    --sign "$APPLE_SIGNING_IDENTITY" "$APP"
  codesign --verify --deep --strict --verbose=2 "$APP"
else
  echo "APPLE_SIGNING_IDENTITY is not set; creating an unsigned development DMG."
fi

mkdir -p "$ROOT/dist/dmg"
rm -f "$ROOT/dist/dmg/ImageShield.dmg"
hdiutil create \
  -volname "ImageShield" \
  -srcfolder "$APP" \
  -ov \
  -format UDZO \
  "$ROOT/dist/dmg/ImageShield.dmg"

echo "Created $ROOT/dist/dmg/ImageShield.dmg"
