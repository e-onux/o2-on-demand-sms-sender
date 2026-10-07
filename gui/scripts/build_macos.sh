#!/bin/zsh
set -euo pipefail

script_dir="${0:A:h}"
repo_root="${script_dir:h:h}"
gui_dir="$repo_root/gui"
output_dir="$gui_dir/build/macos-arm64"
app_name="O2 SMS Kontrol Paneli"

# The build venv, PyInstaller work files and the unsigned bundle live on the
# local APFS disk. On exFAT/SMB volumes macOS adds "._*" AppleDouble files that
# pip reads as broken package metadata and codesign rejects, and pip can fail
# there with "No space left on device" while unpacking deep package trees.
build_root="${O2_SMS_BUILD_CACHE:-$HOME/Library/Caches/o2-sms-control-panel-build}"
build_venv="$build_root/venv"
work_dir="$build_root/work"
dist_dir="$build_root/dist"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    print -u2 "This script must be run on macOS ARM64."
    exit 2
fi

mkdir -p "$build_root"
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
    --name "$app_name" \
    --osx-bundle-identifier "com.emironuk.o2-sms-control-panel" \
    --paths "$repo_root" \
    --hidden-import runtime_status \
    --hidden-import pystray._darwin \
    --distpath "$dist_dir" \
    --workpath "$work_dir" \
    --specpath "$work_dir" \
    "$gui_dir/src/control_panel.py"

/usr/bin/codesign --force --deep --sign - "$dist_dir/$app_name.app"

executable="$dist_dir/$app_name.app/Contents/MacOS/$app_name"
smoke_marker="$work_dir/tray-lifecycle-smoke.ok"
rm -f "$smoke_marker"
"$executable" --smoke-test --project-dir "$repo_root"
O2_SMS_GUI_SMOKE_MARKER="$smoke_marker" \
    "$executable" --tray-lifecycle-smoke-test --project-dir "$repo_root"
test -s "$smoke_marker"

# Copy without resource forks or extended attributes so a non-APFS target
# volume gets no AppleDouble files that would invalidate the signature.
rm -rf "$output_dir/$app_name.app"
mkdir -p "$output_dir"
/usr/bin/ditto --norsrc --noextattr --noqtn "$dist_dir/$app_name.app" "$output_dir/$app_name.app"
/usr/bin/codesign --verify --deep "$output_dir/$app_name.app"

# Disk image with an Applications shortcut for drag-and-drop installation.
dmg_stage="$build_root/dmg"
dmg_path="$output_dir/$app_name.dmg"
rm -rf "$dmg_stage"
mkdir -p "$dmg_stage"
/usr/bin/ditto --norsrc --noextattr --noqtn "$dist_dir/$app_name.app" "$dmg_stage/$app_name.app"
ln -s /Applications "$dmg_stage/Applications"
rm -f "$dmg_path"
/usr/bin/hdiutil create -quiet -volname "$app_name" -srcfolder "$dmg_stage" -ov -format UDZO "$dmg_path"
/usr/bin/hdiutil verify -quiet "$dmg_path"

print "macOS build ready: $output_dir/$app_name.app"
print "Disk image: $dmg_path"
