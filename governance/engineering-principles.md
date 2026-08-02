# Engineering Principles

Project-specific engineering rules. These are more detailed and faster-changing than the constitution.

## Boundaries

- Business rules live in capabilities, not in controllers/UI.
- A capability does not reach into another capability's internals - it depends on its contract.
- No circular dependencies between capabilities.

## Change discipline

- Smallest change that satisfies the contract.
- Evaluate the existing structure before adding a new abstraction or layer.
- Check the decision record before introducing a new dependency.

## Tests

- Tests describe behavior, not implementation details.
- Every capability keeps at least one normal and one error scenario in its contract.

## Documentation

- Minimum useful documentation - no decorative docs.
- Docs that drift from code are bugs.

## Modem automation

- Treat the modem's verified daily byte counter as the source of truth; never infer usage from display strings.
- After a modem counter reset or an operator renewal trigger, persist a verified baseline before counting the next allowance.
- SMS-trigger handling must be idempotent. A message fingerprint is processed at most once.
- Keep modem I/O behind `huawei-lte-api`; UI code invokes explicit application actions instead of calling the modem API directly.

## Long-running operation

- Host and container processes exchange state only through atomically replaced JSON and bounded JSONL files.
- Event history, trigger fingerprints, SMS retention and log reads must have explicit bounds.
- Persisted dates use zero-padded ISO 8601. Readers may accept known legacy date forms during migration.

## Desktop application

- UI strings are translation keys with English, German, Polish, Russian and Turkish catalogs.
- Destructive actions require a confirmation in the GUI and must never run as part of a smoke test.
- macOS tray behavior is owned by the UIElement helper; the main GUI must remain recoverable from Dock or tray.

## Security

- Modem credentials come from environment variables and must never appear in logs, fixtures or repository files.
- Test fixtures use synthetic SMS bodies and counters; tests never send a real SMS or delete a real inbox.
