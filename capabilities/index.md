# Capabilities

| Capability | Purpose | Automated verification | User validation |
|---|---|---|---|
| [renew-highspeed-data](./renew-highspeed-data/contract.yaml) | Renew O2 high-speed data from usage or exact operator triggers. | `tests.test_worker_usage` | Confirm one real supported O2 message produces one renewal and a verified baseline. |
| [retain-recent-sms](./retain-recent-sms/contract.yaml) | Keep only the newest configured modem messages across inbox and sent boxes. | `tests.test_worker_usage` | Optional real-modem inspection after an explicitly approved cleanup. |
| [record-runtime-status](./record-runtime-status/contract.yaml) | Persist atomic status and bounded event/trigger history. | `tests.test_runtime_status` | Inspect `data/status.json` and events in the GUI. |
| [execute-manual-modem-actions](./execute-manual-modem-actions/contract.yaml) | Send a confirmed renewal or clear SMS storage on request. | `tests.test_worker_usage`, fake-client coverage | Explicitly approve and observe a real action. |
| [observe-service-status](./observe-service-status/contract.yaml) | Show usage, actions, events, errors and bounded Docker logs. | `tests.test_runtime_status` | Compare the GUI with the current Docker worker state. |
| [recover-slow-connection](./recover-slow-connection/contract.yaml) | Detect sustained slowness, send WEITER once, then restart the modem on a capped, escalating schedule. | `tests.test_connection_watchdog` | Watch one real slow episode in the GUI chart and events. |
| [operate-docker-service](./operate-docker-service/contract.yaml) | Pull, start, stop and restart the Compose service. | `tests.test_runtime_status` command parsing | Explicitly invoke each lifecycle action on the host. |
| [manage-desktop-lifecycle](./manage-desktop-lifecycle/contract.yaml) | Localize, package, auto-start, minimize and restore the desktop app. | `tests.test_runtime_status` | Validate packaged builds and tray/login behavior on macOS, Windows and Linux. |

The production GUI is the user-facing cockpit. Automated test commands use synthetic clients and never mutate a
real modem, Docker service, login item or SMS box.
