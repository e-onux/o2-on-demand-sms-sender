# Source Manifest

How evidence is stored and linked in this project.

- Every source has a unique id (`source-XXX`) in `bibliography.yaml`.
- Each source declares what it `supports` (ADR ids and/or capability ids) - forming the evidence graph.
- Record link/DOI, version and access date.
- **Default to metadata only.** Store a local PDF/DOCX copy **only** when the license/ownership permits
  (see below); otherwise keep `local_copy: null`.
- The relationship between a source and the decisions/capabilities it backs is bidirectional and queryable.

## When a local copy is allowed

- the source license permits redistribution, **or**
- the document is the user's/organization's own, **or**
- the source is open access, **or**
- offline/legal archival is genuinely required.

Otherwise, store metadata + checksum only. Place permitted copies under `papers/`, `benchmarks/`, `official-docs/`.

## Evidence graph

```
Source → Claim → Decision (ADR) → Capability → Implementation → Test → User validation
```
