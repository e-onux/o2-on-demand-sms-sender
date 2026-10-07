# ADR-0006: Recover slow connections with escalating, capped modem restarts

```yaml
id: ADR-0006
title: Recover slow connections with escalating, capped modem restarts
status: accepted
date: 2026-10-06

context:
  description: >
    The operator observed that a modem restart often fixes network-side slowdowns, but on rainy days the
    connection can stay poor for a whole day, where repeated restarts would only add outages. On 2026-10-06 a
    slow connection showed normal latency (about 30 ms) but only about 10 Mbit/s download, so latency alone
    cannot detect this kind of slowdown.

decision:
  selected: >
    Time a small HTTP request every run plus a 1 MB download probe every 15 minutes (every run only while
    confirming), send WEITER once, then restart with a 30 min / 3 h / 6 h / 12 h / 24 h backoff and at most 4
    restarts per rolling 24 hours. Reset the ladder only after one hour of healthy probes. Probes that fail
    outright count as "unknown" and never trigger an action. The existing modem-latency watch keeps working
    unchanged; both share one reboot marker so neither restarts a modem the other has just restarted. 4G
    RSRP/SINR is recorded per run and reported in the restart SMS when weak, but does not block a restart.
  summary: A pure state machine in connection_watchdog.py decides; the worker executes the action.

alternatives:
  - ICMP ping only - cheaper, but missed the observed low-throughput slowdown and needs a ping binary or raw sockets.
  - TCP connect latency - timed out or took seconds inside the Docker Desktop worker container on 2026-10-06
    while the request round trip on an open connection still showed the real ~30 ms.
  - Count failed probes as slow - would restart the modem when only the container network is broken
    (observed 2026-10-06 - container DNS failing while the host line worked).
  - Read modem signal values (RSRP/SINR) to skip restarts on weak radio - useful later, but does not measure the actual slowdown.
  - Restart on every slow check - simple, but loops on rainy days.

evidence:
  - id: source-operator-slow-connection-requirement
    type: user-research
  - id: source-cloudflare-speed-test
    type: official-documentation
  - id: source-project-regression-tests
    type: internal-evaluation

assumptions:
  - About 100 MB/day of probe traffic (96 x 1 MB) is acceptable on an unlimited on-demand plan.
  - speed.cloudflare.com/__down stays publicly reachable; the URL is configurable.
  - A 1 MB probe measured after the first byte is representative enough to separate "slow" from "normal".

consequences:
  positive:
    - Slowdowns that latency does not show are detected.
    - Worst case is bounded and predictable (see the 48 h test timeline).
    - Thresholds adapt to the line's usual healthy speed.
  negative:
    - The probe uses data volume and depends on an external endpoint.
    - A genuinely bad day still gets up to 4 restarts.

review:
  interval: 6 months
  next_review: 2027-04-06
  triggers:
    - false or useless restarts are reported
    - the probe endpoint changes or blocks automated requests
    - probe data volume becomes a concern

affected_capabilities:
  - recover-slow-connection
  - observe-service-status
  - record-runtime-status

migration:
  required: false

rollback:
  available: true
  plan: Set WATCHDOG_ENABLED=false; the existing renewal flow is unchanged and ignores the extra status fields.
```
