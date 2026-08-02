# Project Constitution

> The highest-priority, slow-to-change rules for this repository. An agent may not violate these without an
> explicit, human-approved change to this file. Keep it short; everything here must earn its place.

1. Every feature is associated with a **capability contract**. No contract → not a feature.
2. A feature without a **test** and an **observable output** is not "done".
3. No new **dependency** is added without a justification (and, if architectural, an ADR).
4. Architectural and technology decisions are recorded as **ADRs** with assumptions and review triggers.
5. Critical business rules do not live only in UI or controllers - they belong to a capability.
6. When a capability exceeds its **budget**, no new code is added until a **split/refactor proposal** exists.
7. Decisions requiring **human approval** (see `human-approval-policy.md`) are never applied by the agent alone.
8. **Evidence over confidence** - a confident explanation never substitutes for a source or a test.
9. The repository - not the chat history - is the project's memory.

_Amend via a PR that updates this file and explains the change. Treat amendments like constitutional changes: rare and deliberate._
