# Architecture Invariants

Rules that must always hold. `trellis` drift checks compare the codebase against these. Express them concretely
enough to be checkable.

- Only `o2_on_demand_hack.py` and `modem_actions.py` perform Huawei modem operations.
  `connection_watchdog.py` only measures the network and returns a decision.
- The desktop GUI invokes modem mutations through explicit subprocess actions; rendering code does not hold a
  live modem session.
- Worker-to-GUI status is valid JSON written by atomic replacement; event history is bounded JSONL.
- Every persisted usage value is an integer byte count. Human-readable units are presentation only.
- Daily dates are written as zero-padded ISO 8601 and evaluated in the configured local timezone.
- Operator-trigger matching uses normalized exact texts, and one trigger fingerprint is processed at most once.
- SMS retention, event history, processed fingerprints and displayed Docker logs all have finite bounds.
- The macOS tray helper contains no modem or renewal business logic.
- Runtime secrets are loaded from environment variables and never copied into status or event files.

## Forbidden dependencies

| From | To | Reason |
|---|---|---|
| GUI rendering | `huawei_lte_api` | modem mutations must use the application action boundary |
| tray helper | worker modules | tray ownership must remain independent of modem automation |
| runtime state | credentials | status and event files must never expose secrets |
