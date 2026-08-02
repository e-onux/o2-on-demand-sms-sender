# TRELLIS.md - Bootstrap Manifesto

> Single-file bootstrap for the **Trellis** standard. Drop this file into a repository and tell your coding
> agent: *"Read `TRELLIS.md` and bootstrap this repository according to it."*
>
> Trellis is an **agent-independent, capability-first, evidence-governed** standard that keeps AI-generated
> software understandable, testable and maintainable as it grows. This file is enough to start; the running
> system must then split knowledge into the small, purpose-built files described below (never keep everything
> in one giant manifesto - it inflates context and gets ignored).
>
> Full standard: https://github.com/e-onux/trellis · `standard/README.md`

---

## What you (the agent) must do

### Phase 0 - Detect & confirm

1. Detect the stack (languages, frameworks, datastores, build, CI).
2. Detect whether this is **greenfield** (empty/new) or **brownfield** (existing code).
3. Choose a **profile** - `backend` | `frontend` | `data-pipeline` | `llm-app` - and a **preset**
   (`light` for brownfield, `standard` otherwise). State your choice and why; ask if uncertain.
4. Do **not** mass-refactor a brownfield repo. Adopt incrementally (see adoption levels).

### Phase 1 - Scaffold governance

Create the directory model (omit pillars disabled by the profile/preset):

```
governance/  product/  tech/  tech/decisions/  sources/  extensions/  capabilities/  quality/  lifecycle/
```

Seed each from the Trellis templates/skeleton: constitution, engineering-principles, agent-authority,
definition-of-done, change-policy, human-approval-policy; product vision/constraints/domain/terminology/non-goals;
tech overview/architecture-map/technology-radar/upgrade/refactoring/dependency policies; sources MANIFEST +
bibliography; extensions EXTENSIONS.md + registry; quality policies + `quality-gates.yaml`; lifecycle calendar +
debt. Write a `.trellis.yaml` capturing profile, preset, agents and enabled modules.

### Phase 2 - Extract decisions (brownfield)

For each significant existing decision (datastore, framework, key dependency, architectural pattern):
create an **ADR** with `context`, `decision`, `alternatives`, `assumptions`, `consequences`, and
`review.triggers`. If you cannot find the rationale, mark it `under-review` and record a "missing evidence"
note - **do not invent justification**. Link sources in `sources/bibliography.yaml`.

### Phase 3 - Discover capabilities

Identify meaningful, user/system-visible behaviors (e.g. user-registration, calculate-shipping-cost,
classify-document). For each, create `capabilities/<id>/` with a `contract.yaml` (intent, `responsibility.does` /
`does_not`, inputs, outputs, ≥1 normal + ≥1 error example, invariants, dependencies, `budgets`, `verification`,
`review`). Register them in `capabilities/capability-map.yaml`. Report capabilities you found but did **not**
contract yet.

### Phase 4 - Tests & cockpit

Derive contract + regression + (profile-required) property-based tests from each contract. Where a test cockpit
is enabled, register each capability so a human can run input → see expected vs actual.

### Phase 5 - Budgets, gates & adapters

Set capability budgets from the profile defaults. Wire `quality/quality-gates.yaml` into CI. Generate the agent
adapter files (see below) with `AGENTS.md` as canonical. Report anything ambiguous for human review.

---

## The rules you must follow while working

These mirror `governance/`. They are not optional.

1. **Capability-first.** Every feature maps to a capability contract. No contract → not a feature.
2. **Done ≠ code written.** A capability is done only when it has a contract, examples, passing tests, a
   human-verifiable surface, respects its budget, preserves invariants, and has current ADRs/sources.
3. **Budgets are hard limits.** Decision rule for new behavior:
   ```
   fits responsibility.does?
     yes → within budget? extend : STOP → write refactor/split proposal
     no  → propose a NEW capability
   ```
4. **Obligation to NOT write code.** When a stop condition fires (budget exceeded, conflicts with `does_not`,
   unknown rationale, new architectural dependency, no verifiable example, unmeasurable regression risk,
   security/data uncertainty) you must produce a **proposal** (split / refactor / ADR / migration /
   missing-requirement / risk / user-validation), not an implementation. A proposal is a valid deliverable.
5. **Decisions are conditional.** Every ADR carries assumptions + review triggers. Supersede, never delete.
6. **Evidence over confidence.** Don't substitute a confident assertion for a source or a test.
7. **Registration over convention.** To add/remove an extension, read the nearest `EXTENSIONS.md` + parent
   rules + the machine-readable `extension-registry.yaml`, and update every required registration point.
8. **Single source of truth.** Never duplicate a rule into agent adapter files - they point here.
9. **Repository is the memory.** Persist decisions/sources/contracts in the repo, not in chat.

## Completion report (always)

End substantive work with:

```
Implementation completed.
- N capability contracts evaluated
- N passed
- N require user validation
- N architecture/budget violations
- N unresolved regressions
- N ADRs updated / added
- N source records added
- Files updated for extensions: [...]
```

## Agent adapters to generate

`AGENTS.md` (canonical) + thin pointers: `CLAUDE.md`, `.github/copilot-instructions.md`,
`.cursor/rules/trellis.mdc`, `.windsurf/rules/trellis.md`, `GEMINI.md`. Pointers must not restate rules.

## Progressive adoption (don't do everything at once)

```
L1 Governance + ADRs → L2 Capability contracts → L3 Automated tests
→ L4 User test cockpit → L5 Capability & architecture budgets → L6 Lifecycle + upgrade automation
```

If the CLI is available, `trellis init` / `trellis validate` / `trellis budget-check` / `trellis audit` /
`trellis extension validate` perform and check the above deterministically.
