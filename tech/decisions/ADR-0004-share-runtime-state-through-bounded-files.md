# ADR-0004: Share runtime state through bounded files

```yaml
id: ADR-0004
title: Share runtime state through bounded files
status: accepted
date: 2026-08-02

context:
  description: >
    The container worker and host GUI need a small, inspectable state channel. The worker is long-running, so
    partial writes, concurrent updates and unbounded histories must not corrupt state or grow indefinitely.

decision:
  selected: Exchange snapshots as atomically replaced JSON and events as locked, bounded JSONL in a bind-mounted data directory.
  summary: Use cross-platform file locking, daily rollover and fixed record limits without introducing a database.

alternatives:
  - Add an HTTP API to the worker.
  - Add SQLite or an external database.
  - Parse Docker logs as the only status source.

evidence:
  - id: source-python-file-locking
    type: official-documentation
  - id: source-project-regression-tests
    type: internal-evaluation

assumptions:
  - One worker and a small number of local GUI/action processes access the files.
  - The shared data directory supports atomic replacement and the platform lock primitive.
  - Status and event volume stays within the declared performance budgets.

consequences:
  positive:
    - State remains human-inspectable and requires no additional service.
    - Atomic writes and locks prevent readers from observing partially written snapshots.
    - Explicit record caps make disk and memory use independent of uptime.
  negative:
    - The design is unsuitable for remote multi-user access or high write throughput.
    - Locking behavior has platform-specific implementation details.

review:
  interval: 12 months
  next_review: 2027-08-02
  triggers:
    - multiple remote operators are required
    - file-locking or corruption regressions occur
    - state volume exceeds its performance budget

affected_capabilities:
  - record-runtime-status
  - renew-highspeed-data
  - execute-manual-modem-actions
  - observe-service-status

migration:
  required: false

rollback:
  available: true
  plan: Preserve existing JSON fields while reverting to the previous bounded-file implementation.
```
