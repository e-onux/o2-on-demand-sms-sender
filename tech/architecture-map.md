# Architecture Map

## Layers and boundaries

1. `o2_on_demand_hack.py` is the long-running worker and owns polling, trigger evaluation, renewal and SMS
   retention orchestration.
2. `modem_actions.py` is the explicit command boundary for user-requested modem mutations.
3. `runtime_status.py` is the persistence boundary shared by worker and GUI. It owns locking, atomic JSON,
   bounded JSONL and daily counters.
4. `gui/src/control_panel.py` reads runtime state and invokes Docker or modem action subprocesses. It must not
   own renewal business rules.
5. `gui/src/platform_integration.py` owns login-start integration. The macOS AppKit tray helper owns the
   menu-bar icon and communicates with the main GUI through local control messages.

## Capabilities and services

| Capability | Primary implementation | Talks to |
|---|---|---|
| renew-highspeed-data | `o2_on_demand_hack.py` | Huawei modem, runtime status |
| retain-recent-sms | `o2_on_demand_hack.py` | Huawei modem |
| record-runtime-status | `runtime_status.py` | Local bind-mounted files |
| execute-manual-modem-actions | `modem_actions.py` | Huawei modem, runtime status |
| observe-service-status | `gui/src/control_panel.py` | Runtime files, Docker CLI |
| operate-docker-service | `gui/src/control_panel.py` | Docker Compose CLI |
| manage-desktop-lifecycle | `gui/src/control_panel.py`, platform helpers | Host startup and tray APIs |

## Runtime flow

```text
Huawei modem <-> worker -> atomic status/events <- desktop control panel -> Docker Compose
                       ^                             |
                       +------ manual actions -------+

macOS menu-bar helper <-> local control channel <-> desktop control panel
```
