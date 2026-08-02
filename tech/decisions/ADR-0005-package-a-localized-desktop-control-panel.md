# ADR-0005: Package a localized desktop control panel

```yaml
id: ADR-0005
title: Package a localized desktop control panel
status: under-review
date: 2026-08-02

context:
  description: >
    A non-technical operator needs visible usage, events and Docker controls on macOS, Windows and Linux, plus
    localized labels, login startup and recoverable minimize-to-tray behavior.

decision:
  selected: Use Tkinter for the GUI, PyInstaller for native bundles and a separate AppKit UIElement helper for the macOS menu-bar icon.
  summary: Build each platform on a native GitHub Actions runner and keep platform integration behind helper modules.

alternatives:
  - Serve a browser-based local control panel.
  - Use Qt or another third-party desktop framework.
  - Use only a command-line interface.
  - Keep the macOS tray icon inside the Tkinter process.

evidence:
  - id: source-tkinter-docs
    type: official-documentation
  - id: source-pyinstaller-docs
    type: official-documentation
  - id: source-project-regression-tests
    type: internal-evaluation

assumptions:
  - Tkinter is available in the build environment and remains supported by packaged Python versions.
  - PyInstaller bundles are built on the target operating system.
  - A dedicated UIElement helper is more reliable than mixed Tk/AppKit event loops on macOS.

consequences:
  positive:
    - The application uses Python's standard GUI binding and ships as a native-looking local utility.
    - Platform-native builds and a dedicated macOS tray owner isolate operating-system differences.
  negative:
    - The current control-panel module contains several UI responsibilities and exceeds its file budget.
    - Tray, login-start and accessibility behavior still require human validation on each operating system.
    - The original framework comparison is not recorded.

review:
  interval: 6 months
  next_review: 2027-02-02
  triggers:
    - a supported platform build or launch fails
    - the tray cannot restore a hidden window
    - accessibility or localization requirements change
    - RP-001 is implemented

affected_capabilities:
  - observe-service-status
  - operate-docker-service
  - manage-desktop-lifecycle

migration:
  required: false

rollback:
  available: true
  plan: Restore the previous platform helper while retaining the GUI preferences and control-panel entry point.
```

## Review note

This brownfield ADR remains under review until the platform matrix and original framework rationale have been
confirmed by a human operator.
