#!/usr/bin/env bash
set -euo pipefail

architecture="${1:-amd64}"
case "$architecture" in
    amd64|arm64) ;;
    *)
        echo "Usage: $0 [amd64|arm64]" >&2
        exit 2
        ;;
esac

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
builder_image="o2-sms-gui-builder:${architecture}"
output_dir="$repo_root/gui/build/linux-${architecture}"

docker build \
    --platform "linux/${architecture}" \
    --file "$repo_root/gui/packaging/linux.Dockerfile" \
    --tag "$builder_image" \
    "$repo_root"

mkdir -p "$output_dir" "$repo_root/gui/.build-work/linux-${architecture}"

docker run --rm \
    --platform "linux/${architecture}" \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp \
    --volume "$repo_root:/workspace" \
    --workdir /workspace \
    "$builder_image" \
    /opt/gui-build/bin/python -m PyInstaller \
        --noconfirm \
        --clean \
        --onefile \
        --windowed \
        --name o2-sms-control-panel \
        --paths /workspace \
        --hidden-import runtime_status \
        --hidden-import pystray._xorg \
        --distpath "/workspace/gui/build/linux-${architecture}" \
        --workpath "/workspace/gui/.build-work/linux-${architecture}" \
        --specpath "/workspace/gui/.build-work/linux-${architecture}" \
        /workspace/gui/src/control_panel.py

docker run --rm \
    --platform "linux/${architecture}" \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp \
    --volume "$repo_root:/workspace" \
    --workdir /workspace \
    "$builder_image" \
    "/workspace/gui/build/linux-${architecture}/o2-sms-control-panel" \
        --smoke-test \
        --project-dir /workspace

docker run --rm \
    --platform "linux/${architecture}" \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp \
    --volume "$repo_root:/workspace" \
    --workdir /workspace \
    "$builder_image" \
    sh -c '
        marker=/tmp/o2-sms-gui-smoke-ok
        export O2_SMS_GUI_SMOKE_MARKER="$marker"
        timeout 20s xvfb-run -a \
            "/workspace/gui/build/linux-'"${architecture}"'/o2-sms-control-panel" \
            --gui-smoke-test \
            --project-dir /workspace
        result=$?
        if [ "$result" -eq 0 ] || [ -s "$marker" ]; then
            exit 0
        fi
        exit "$result"
    '

echo "Linux build ready: $output_dir/o2-sms-control-panel"
