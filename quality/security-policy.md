# Security Policy

The principles an agent must follow live in the **[Security Manifesto](../governance/security-manifesto.md)**
(profile-aware, grounded in OWASP / CISA). This file records the **enforced** part.

## Enforced

- **No committed secrets.** Credentials, keys and tokens never enter the repository - environment or
  secret store only; `.env.example` documents names, not values. Checked by `trellis secret-scan`
  (fail-closed). Mark an intentional example with an inline `trellis-allow-secret` comment.

## Human-approval gate

Security-sensitive changes (auth, data-retention, crypto, access boundaries) require human approval -
see [`governance/agent-authority.md`](../governance/agent-authority.md).

## Delegated

Deep vulnerability scanning (SAST) is delegated to a dedicated tool (Semgrep, CodeQL) in CI - Trellis
governs, it does not re-implement a scanner.
