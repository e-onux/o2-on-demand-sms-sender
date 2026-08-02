# Extensions - root contract

> **Registration over convention.** Adding a plugin/module/provider/adapter is never "just a new folder". The
> files that must be updated to wire it in - and to remove it cleanly - are declared here and in
> `extension-registry.yaml`, not left to memory or naming convention.

## How it works

- This root `EXTENSIONS.md` defines **general** rules for all extension points.
- A subsystem (e.g. `payments/`) may add its own `EXTENSIONS.md` with point-specific rules.
- An agent reads the **nearest** `EXTENSIONS.md` **and** the applicable general rules in parent directories.
- `extension-registry.yaml` is the machine-readable companion (schema: `extension-contract.schema.json`),
  checked by `trellis extension validate`.

## General rules (apply to every extension)

A new extension is not complete until:

```
[ ] Implementation + unit/contract tests exist
[ ] Registered in the relevant registry
[ ] Config + config schema updated; secrets marked
[ ] .env.example updated (no real secrets)
[ ] User + developer docs updated
[ ] Affected capability contract(s) updated
[ ] Test-cockpit scenarios registered (when cockpit enabled)
[ ] CHANGELOG entry added
[ ] Removal/cleanup steps defined
```

See `types/` for per-kind guidance and `https://github.com/e-onux/trellis/blob/main/standard/templates/extension-registration-template.md` /
`extension-removal-template.md` for copyable starting points.
