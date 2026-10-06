# Performance Budgets

Latency, throughput and memory limits. Define globally here and override per capability in `contract.yaml`.

| Scope | Metric | Budget |
|---|---|---|
| Worker polling | Interval | 60 seconds unless explicitly configured |
| Runtime event history | Persisted records | At most 500 events |
| Processed trigger history | Persisted fingerprints | At most 200 fingerprints |
| Modem SMS retention | Stored messages | Newest 3 combined by default |
| Network history | Persisted samples | At most 1,440 (24 h at one per minute) |
| Speed probe | Data volume | 1 MB per probe, every 15 min while healthy (about 100 MB/day) |
| Automatic modem restarts | Frequency | At most 4 per rolling 24 h, escalating gaps from 30 min |
| GUI Docker log view | Fetched lines | At most 200 lines per request |
| Worker persistent memory | Growth with uptime | O(1); all in-memory collections are bounded |
| State/event write | Durability | Atomic replacement or locked bounded rewrite |

Exceeding a performance budget is an upgrade/refactor trigger (see `tech/upgrade-policy.md`).
