$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$GuiDir = Join-Path $RepoRoot "gui"
$BuildVenv = Join-Path $GuiDir ".venv-build-windows"
$OutputDir = Join-Path $GuiDir "build\windows-x86_64"
$WorkDir = Join-Path $GuiDir ".build-work\windows-x86_64"

if (-not (Test-Path (Join-Path $BuildVenv "Scripts\python.exe"))) {
    py -3.12 -m venv $BuildVenv
}

$Python = Join-Path $BuildVenv "Scripts\python.exe"
& $Python -m pip install --disable-pip-version-check -r (Join-Path $GuiDir "requirements-build.txt")
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name O2SMSControlPanel `
    --paths $RepoRoot `
    --hidden-import runtime_status `
    --hidden-import pystray._win32 `
    --distpath $OutputDir `
    --workpath $WorkDir `
    --specpath $WorkDir `
    (Join-Path $GuiDir "src\control_panel.py")

Write-Host "Windows build ready: $OutputDir\O2SMSControlPanel.exe"
