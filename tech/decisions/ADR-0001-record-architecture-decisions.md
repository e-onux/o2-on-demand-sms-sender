# ADR-0001: Record architecture decisions

> This record documents why project decisions live in the repository.

```yaml
id: ADR-0001
title: Record architecture decisions
status: accepted
date: 2026-08-02

context:
  description: >
    This project is developed with AI coding agents. Decisions made in chat are lost between sessions,
    and code outlives the reasoning behind it. We need decisions to live in the repository, as conditional
    and reviewable records rather than tribal knowledge.

decision:
  selected: Use Trellis ADRs (YAML front matter validated against the ADR schema) for every significant decision.

alternatives:
  - Keep decisions in chat history / PR descriptions only
  - Free-form wiki pages
  - Classic markdown-only ADRs without machine-checkable fields

evidence:
  - id: source-trellis-standard
    type: standard

assumptions:
  - The team values long-term maintainability over short-term speed.
  - Agents will read ADRs as context before making related changes.

consequences:
  positive:
    - Decisions, assumptions and review triggers are explicit and queryable.
    - Superseded decisions remain visible (history is preserved).
  negative:
    - Small overhead per decision.

review:
  interval: 12 months
  next_review: 2027-08-02
  triggers:
    - the team abandons agent-assisted development
    - a better decision-record format is adopted project-wide

affected_capabilities: []

migration:
  required: false

rollback:
  available: true
```

## Notes

Trellis was adopted with the `backend` profile and `light` brownfield preset. Runtime behavior is unchanged by
this decision; governance artifacts make the existing system explicit and reviewable.
