# Definition of Done

A capability is **not done** because code was written. It is done when:

```
[ ] Capability contract exists and validates against the schema
[ ] Input schema defined
[ ] Output schema defined
[ ] At least one normal scenario
[ ] At least one error scenario
[ ] Edge cases identified
[ ] Invariants defined
[ ] Unit tests pass
[ ] Contract tests pass
[ ] Regression tests pass
[ ] Property-based tests pass (if required by profile)
[ ] Runnable in the user test cockpit
[ ] Expected vs actual output is comparable by a human
[ ] Capability budget not exceeded
[ ] Architecture invariants preserved
[ ] Related ADRs are current
[ ] Sources linked (evidence)
[ ] No regression in existing capabilities
[ ] Items needing user validation are flagged
[ ] Migration plan exists if needed
[ ] Rollback plan exists if needed
```

## Completion report

The agent reports completion in this shape, not just "done":

```
Implementation completed.
- 12 capability contracts evaluated
- 11 passed
- 1 requires user validation
- 0 architecture budget violations
- 0 unresolved regressions
- 2 ADRs updated
- 1 source record added
```
