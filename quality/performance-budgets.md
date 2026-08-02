# Performance Budgets

Latency, throughput and memory limits. Define globally here and override per capability in `contract.yaml`.

| Scope | Metric | Budget |
|---|---|---|
| Worker polling | Interval | 60 seconds unless explicitly configured |
| Runtime event history | Persisted records | At most 500 events |
| Processed trigger history | Persisted fingerprints | At most 200 fingerprints |
| Modem SMS retention | Stored messages | Newest 3 combined by default |
| GUI Docker log view | Fetched lines | At most 200 lines per request |
| Worker persistent memory | Growth with uptime | O(1); all in-memory collections are bounded |
| State/event write | Durability | Atomic replacement or locked bounded rewrite |

Exceeding a performance budget is an upgrade/refactor trigger (see `tech/upgrade-policy.md`).
