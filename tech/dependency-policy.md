# Dependency Policy

A new dependency is a decision, not a convenience.

Before adding one:

- Is it justified? Does an existing dependency already cover the need?
- Does it fit the architecture invariants?
- License compatible with this project?
- Maintained (recent activity, security posture)?
- Does it push any capability over its `max_direct_dependencies` budget?

Architectural dependencies (frameworks, datastores, external services) require an ADR. Record the dependency's
license under `sources/` if it carries obligations.
