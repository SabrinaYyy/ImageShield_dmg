$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYINSTALLER_CONFIG_DIR = Join-Path $Root ".pyinstaller"

python scripts/validate_bundle.py
python -m PyInstaller --noconfirm --clean ImageShield.spec

$Executable = Join-Path $Root "dist\ImageShield\ImageShield.exe"
if (-not (Test-Path $Executable)) {
    throw "Build failed: $Executable was not created."
}

Write-Host "Created $Executable"
Write-Host "Run Inno Setup against packaging\windows\ImageShield.iss to create the installer."
