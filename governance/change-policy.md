# Change Policy

How changes flow through this repository.

## Flow

1. **Understand** - find affected capabilities, read their contracts, ADRs and sources.
2. **Classify** - existing capability? new capability? refactor? new decision? needs human approval?
3. **Propose** (if a stop condition applies) - split/refactor/ADR/migration proposal.
4. **Contract first** - write/update the contract (inputs, outputs, examples, invariants, budgets).
5. **Test first** - contract + regression + property tests before implementation.
6. **Implement** - smallest change; respect budgets and invariants.
7. **Verify** - run tests, compare expected vs actual, check drift, update cockpit.
8. **Complete** - update changelog, ADRs, sources, capability version; emit the completion report.

## Versioning

- Capabilities use SemVer. Breaking contract change → major.
- ADRs are append-only: supersede, never delete.
