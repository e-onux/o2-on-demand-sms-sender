# O2 SMS Control Panel

This directory contains the desktop control panel source, cross-platform
packaging scripts, and generated applications.

## Features

- Pull, build, start, stop, and restart the Docker Compose service.
- Display service health, current daily usage, SMS counts, the latest SMS
  reason, threshold state, recent events, and Docker logs.
- Send a confirmed manual `WEITER` SMS and clear the modem SMS inbox.
- Copy or clear the bounded event history.
- Switch the interface at runtime between Turkish, English, German, Polish,
  and Russian.
- Minimize to the system tray when the window is closed or from the Settings
  menu.
- Optionally start at user login in minimized mode.

On macOS, the status item runs in a dedicated `UIElement` helper process with
its own AppKit event loop. Hiding the main window switches it out of the Dock;
the helper remains in the menu bar and signals the main process when the window
or Quit command is selected. If the helper does not complete its readiness
handshake, the application keeps a recoverable Dock window instead of hiding
it completely.

Preferences are stored in the operating system's per-user application settings
directory. The startup integration uses a LaunchAgent on macOS, the current
user's `Run` registry key on Windows, and an XDG autostart entry on Linux.

## Directory layout

```text
gui/
├── src/                    # Python GUI, translations, and platform helpers
│   └── native/             # Source-only macOS launcher used during development
├── scripts/                # Local platform build scripts
├── packaging/              # Linux build container
├── build/                  # Generated application artifacts
└── requirements-build.txt  # Pinned GUI and packaging dependencies
```

## Run from source

From the repository root:

```bash
python3 gui/src/control_panel.py
```

The application searches its current directory and parent directories for the
repository. When the executable is stored elsewhere, pass the project location
explicitly:

```bash
O2_SMS_PROJECT_DIR=/path/to/o2-on-demand-sms-sender \
  python3 gui/src/control_panel.py
```

The equivalent Windows PowerShell setting is:

```powershell
$env:O2_SMS_PROJECT_DIR = "C:\path\to\o2-on-demand-sms-sender"
```

All packaged builds also accept `--project-dir PATH`. The startup integration
uses this argument so it continues to locate the correct Compose project.

## Build

Build macOS ARM64 locally:

```bash
gui/scripts/build_macos.sh
```

Build Linux x86_64 or ARM64 in Docker:

```bash
gui/scripts/build_linux.sh amd64
gui/scripts/build_linux.sh arm64
```

Build Windows x86_64 from Windows PowerShell:

```powershell
gui\scripts\build_windows.ps1
```

PyInstaller must run on the target operating system; it does not provide a
reliable Windows cross-compiler on macOS. The workflow at
`.github/workflows/gui-build.yml` therefore creates macOS ARM64, Linux x86_64,
and Windows x86_64 artifacts on native GitHub-hosted runners.

## Verification

Packaged binaries provide a non-interactive startup check:

```bash
./o2-sms-control-panel --smoke-test --project-dir /path/to/repository
```

Exit code `0` means that the packaged Python runtime loaded and the required
project files were found. Exit code `1` means that the project contract was not
satisfied.

Three additional build checks are available: `--docker-smoke-test` verifies
that the packaged process can reach Docker Engine, while `--gui-smoke-test`
creates the full translated window and tray integration, then exits
automatically. On macOS, `--tray-lifecycle-smoke-test` also verifies the helper
handshake, the `Regular → Accessory → Regular` Dock policy transition, the
`normal → withdrawn → normal` window transition, and the restore signal. The
macOS build script and CI workflow require this lifecycle test to pass.

On macOS, a project under `Documents` is covered by Apple's privacy controls.
The installed application may ask for Documents access once. Use the installed
copy under `/Applications` consistently; launching separate build copies can
cause macOS to treat them as separate application identities.
