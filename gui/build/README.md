# Generated GUI builds

Local build scripts write platform artifacts into this directory:

- `macos-arm64/O2 SMS Kontrol Paneli.app`
- `linux-amd64/o2-sms-control-panel`
- `linux-arm64/o2-sms-control-panel`
- `windows-x86_64/O2SMSControlPanel.exe`

Generated binaries are intentionally excluded from Git history. GitHub Actions
builds macOS ARM64, Linux x86_64, and Windows x86_64 on native runners and
publishes them as downloadable workflow artifacts.
