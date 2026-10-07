# Refactor Proposal: Split the worker's restart watchdogs out of o2_on_demand_hack.py

## Problem

`o2_on_demand_hack.py` now hosts three reasons to change: the WEITER renewal, the modem-latency watch
(ping to the modem, reboot after bad samples) and the slow-connection recovery glue (probes, signal,
escalating restarts). The `recover-slow-connection` budget is exceeded (about 1,060/800 lines, 20/16 direct
dependencies) because both watchdogs live in the renewal module.

## Evidence

- `trellis budget-check` on 2026-10-06: recover-slow-connection lines 1061/800, deps 20/16
- both watchdogs share one reboot marker (`last_modem_latency_reboot_epoch`) and the restart notification

## Proposed split

- `modem_restart.py` - restart notification SMS (with weak-signal note), shared reboot marker, signal reading.
- `modem_latency_watch.py` - modem ping measurement and bad-sample window (pure decision + measurement).
- `o2_on_demand_hack.py` - renewal flow and the `main()` orchestration only.
- `connection_watchdog.py` stays the pure slow-connection decision module.

Modem API calls stay in the worker modules (architecture invariant), only moved between files.

## Risks

- `tests/test_worker_usage.py` and `tests/test_connection_watchdog.py` patch module globals on
  `o2_on_demand_hack`; they must patch the new modules instead.
- The deployed container copies the whole repository, so no Dockerfile change is expected.

## Test plan

- Keep all current tests green while moving one module at a time.
- Run one worker cycle in the container and compare status/event fields before and after.

## Migration and rollback

No data migration. Revert the move commit if any status field or event type changes.
