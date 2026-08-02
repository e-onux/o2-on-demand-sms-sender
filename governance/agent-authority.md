# Agent Authority

Defines what the agent may do autonomously, what requires human approval, and - crucially - when the agent must
**stop and propose instead of writing code**.

## The agent may do autonomously

- Add or improve tests
- Update documentation to match code
- Small, behavior-preserving refactors
- Changes that fit within an existing capability's `responsibility.does` **and** stay within budget
- Propose missing example scenarios

## Requires human approval

(See `human-approval-policy.md` for the sign-off record format.)

- Core framework or database changes
- Adding a new external service or dependency with architectural impact
- Changing data-retention or security boundaries
- Public API breaking changes
- Splitting or merging capabilities
- Adding a source with a license risk

## Obligation to NOT write code (stop conditions)

The agent **must not implement**, and must instead produce the named proposal, when:

| Condition | Required output |
|---|---|
| New behavior conflicts with a capability's `does_not` | New-capability or split proposal |
| Capability budget would be exceeded | Refactor / split proposal + impact analysis |
| A decision's source or rationale is unknown | ADR proposal (or a request for evidence) |
| A new dependency conflicts with architecture invariants | ADR proposal |
| No user-verifiable example is defined | User-validation request |
| Regression risk cannot be measured | Risk report |
| Security or data integrity is uncertain | Risk report + human-approval request |

> Stop conditions are not failure - they are the framework working. A proposal is a valid, expected deliverable.
