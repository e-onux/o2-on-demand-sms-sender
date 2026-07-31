#!/bin/zsh
set -euo pipefail

script_dir="${0:A:h}"
repo_root="${script_dir:h:h}"
gui_dir="$repo_root/gui"
build_venv="$gui_dir/.venv-build"
output_dir="$gui_dir/build/macos-arm64"
work_dir="$gui_dir/.build-work/macos-arm64"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    print -u2 "This script must be run on macOS ARM64."
    exit 2
fi

if [[ ! -x "$build_venv/bin/python" ]]; then
    python3 -m venv "$build_venv"
fi

"$build_venv/bin/python" -m pip install --disable-pip-version-check \
    -r "$gui_dir/requirements-build.txt"

"$build_venv/bin/python" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --onedir \
    --name "O2 SMS Kontrol Paneli" \
    --osx-bundle-identifier "com.emironuk.o2-sms-control-panel" \
    --paths "$repo_root" \
    --hidden-import runtime_status \
    --hidden-import pystray._darwin \
    --distpath "$output_dir" \
    --workpath "$work_dir" \
    --specpath "$work_dir" \
    "$gui_dir/src/control_panel.py"

/usr/bin/codesign --force --deep --sign - \
    "$output_dir/O2 SMS Kontrol Paneli.app"

print "macOS build ready: $output_dir/O2 SMS Kontrol Paneli.app"
