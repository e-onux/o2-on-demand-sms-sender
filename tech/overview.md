# Technology Overview

| Area | Choice | ADR | Radar ring |
|---|---|---|---|
| Language | Python 3.11+ | ADR-0002 | adopt |
| Modem integration | `huawei-lte-api` | ADR-0002 | adopt |
| Worker runtime | Docker Compose + supervisord | ADR-0003 | adopt |
| State exchange | Atomic JSON + bounded JSONL bind mount | ADR-0004 | adopt |
| Desktop GUI | Tkinter | ADR-0005 | adopt |
| Packaging | PyInstaller and platform-native GitHub Actions runners | ADR-0005 | adopt |
| macOS tray | AppKit UIElement helper | ADR-0005 | trial |

The project has no database or hosted service. The modem is the only runtime external system.
