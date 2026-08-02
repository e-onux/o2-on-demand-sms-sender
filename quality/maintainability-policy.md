# Maintainability Policy

Maintainability is a budgeted, first-class concern - not an afterthought.

- A change that pushes a capability over budget requires a refactor/split proposal first.
- Duplicated behavior across capabilities is flagged and consolidated.
- Dead code, unused abstractions and orphan registrations are removed, not left "just in case".
- A new change must not raise maintenance cost unacceptably (the `maintenance` gate).

The measurable signals live in capability `budgets:` and `quality/architecture-invariants.md`.
