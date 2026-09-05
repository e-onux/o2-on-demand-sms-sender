# Refactor Proposal: Split the desktop control panel

## Problem

`gui/src/control_panel.py` is 1,547 lines and changes for three distinct reasons: status presentation, Docker
service orchestration and desktop lifecycle/tray preferences. It exceeds the backend capability default of 800
lines and the semantic budget of one change reason. Adding more behavior to the module would increase drift.

## Evidence

- source file size: 1,547 lines (budget 800)
- distinct change reasons: 3 (budget 1)
- capabilities represented: 3
- domains touched: presentation/localization, Docker subprocesses, host startup/tray integration
- regressions in the current test run: recorded by the current validation report

## Proposed split / restructure

- `status_view_model.py` - parse runtime state, compute presentation values and expose localized view data.
- `docker_service.py` - resolve Docker, run bounded Compose commands and normalize service status/log results.
- `desktop_controller.py` - window visibility, close behavior, tray messaging and login-start preferences.
- `control_panel.py` - compose widgets and delegate to those boundaries; retain the existing application entry point.

The split preserves the current capability contracts and does not change the worker or persisted-state schema.

## Risks

- Tkinter callbacks may capture state implicitly and require careful extraction.
- Packaged PyInstaller imports and macOS helper paths may change.
- Temporary adapters may duplicate small amounts of command or preference wiring.

## Test plan

- Preserve all existing control-panel and platform-integration regression tests.
- Add unit tests for each extracted boundary before moving behavior.
- Keep a compatibility test for `control_panel.main` and packaged resource discovery.
- Rebuild and smoke-test macOS, Windows and Linux artifacts.
- Require a human test that close-to-tray and restore work on each supported platform.

## Migration and rollback

No data or public CLI migration is required. Move one boundary per change and keep compatibility imports until
all tests and packaged smoke tests pass. Roll back an extraction independently if a platform build regresses.
