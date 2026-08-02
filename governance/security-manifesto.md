# Security Manifesto

What an agent (and a human) **must keep in mind** when generating or changing code in this
repository. It lives in the repo so it survives across agent sessions - security that is
remembered, not re-explained every chat.

This is **advisory** - it raises the floor for a cooperative agent, it does not by itself guarantee
security. Exactly one rule here is mechanically enforced (no committed secrets, via
`trellis secret-scan`); the rest are principles. Delegate deep vulnerability detection to real tools
(Semgrep, CodeQL) in CI - do not hand-roll a scanner.

Grounded in [OWASP Top 10](https://owasp.org/www-project-top-ten/),
[OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) and
[CISA Secure by Design](https://www.cisa.gov/securebydesign).

## Core principles (every profile)

1. **External input is untrusted by default.** Validate and normalize at the capability boundary.
   Parameterize queries (never build SQL/shell/LDAP by string concatenation). Block path traversal
   and SSRF; allow-list, don't deny-list.
2. **Never commit secrets.** Credentials, keys and tokens come from the environment or a secret
   store only. `.env.example` documents variable *names*, never values. Enforced by `trellis secret-scan`.
3. **Authorize every entry point.** Deny by default, least privilege, checks on the server side -
   never trust the client. Authorization belongs to the capability, not scattered in the UI.
4. **Encode on output.** Context-aware escaping for HTML/JS/SQL/shell to prevent injection and XSS.
5. **Don't roll your own crypto.** Use vetted libraries and current algorithms; never log secrets,
   tokens or full PII.
6. **Dependencies are attack surface.** Vet a package before adding it (maintenance + security
   posture - see `tech/dependency-policy.md`), pin versions, and watch advisories.
7. **Fail closed, disclose little.** No stack traces or internal details to end users; safe,
   generic error responses.
8. **Security-sensitive changes are a human-approval gate.** Auth, data-retention, crypto, access
   boundaries → stop and request review (see `governance/agent-authority.md`). When in doubt, escalate.

## By profile

**backend** - tenant/row isolation on every query; rate-limit and quota public endpoints; treat
outbound URLs as SSRF risk; rotate and scope service credentials; audit-log security-relevant events.

**frontend** - a strict Content-Security-Policy and output encoding against XSS; CSRF protection on
state-changing requests; `HttpOnly`/`Secure`/`SameSite` cookies; **no secrets in the client bundle**;
treat npm supply chain as hostile (lockfile, integrity).

**data-pipeline** - minimize and tokenize PII; access control on datasets and intermediate stores;
encrypt at rest and in transit; honor data-retention and deletion (right-to-erasure); never copy
production secrets/PII into dev or logs.

**llm-app** - treat retrieved/user/tool content as untrusted input that **must not override system
instructions** (prompt injection); run tools/agents with least privilege and a sandbox; validate
model output before acting on it; keep secrets and excess PII out of prompts and out of model
providers; rate- and cost-limit. (OWASP LLM Top 10: LLM01 prompt injection, LLM02 sensitive
information disclosure, LLM06 excessive agency.)

## What is enforced vs advisory

| Layer | Mechanism | Status |
|---|---|---|
| No committed secrets | `trellis secret-scan` (fail-closed) | **enforced** |
| The principles above | this manifesto + the `AGENTS.md` rule | advisory |
| Deep vuln / SAST | external adapter (Semgrep / CodeQL) | delegated, not in core |

Honest boundary: a manifesto changes behavior, it does not prove safety. Pair it with the
secret-scan gate, human-approval on sensitive changes, and a real SAST tool in CI.
