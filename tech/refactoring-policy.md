# Refactoring Policy

**Refactor before collapse.** A budget breach triggers refactoring *before* the code becomes unmaintainable,
not after.

A refactor proposal (see `https://github.com/e-onux/trellis/blob/main/standard/templates/refactor-proposal-template.md`) is required when a capability:

- exceeds any technical budget;
- accumulates more than `max_change_reasons` distinct reasons to change;
- repeatedly causes regressions in other capabilities;
- reaches into multiple domains.

Refactors preserve existing contract tests and add compatibility tests for any changed entry point.
