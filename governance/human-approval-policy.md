# Human Approval Policy

Some changes may not be applied by the agent alone (see `agent-authority.md` for the list).

## Sign-off record

When a human approves a gated change, record it (in the PR description or `lifecycle/`):

```yaml
approval:
  change: short description
  scope: [capability-ids or ADR ids affected]
  approved_by: name-or-handle
  approved_at: 2026-01-01
  conditions: >
    Any conditions attached to the approval.
```

## Principle

Automated tests confirm *the code behaves*. Human approval confirms *the behavior is right for the business*.
Both are required for gated changes.
