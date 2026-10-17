# ADR-0007: Serve an optional LAN web panel from the worker container

```yaml
id: ADR-0007
title: Serve an optional LAN web panel from the worker container
status: accepted
date: 2026-10-16

context:
  description: >
    The operator wants to reach the control panel from other computers (http://homenas.local). The desktop
    Tk panel only runs on the host. The worker container already has the runtime files and the modem action
    entry point.

decision:
  selected: >
    A stdlib ThreadingHTTPServer (web_panel.py) as a second supervisord program in the worker container,
    disabled unless WEB_PANEL_ENABLED=true, published on port 8095. Viewing is open on the LAN; actions need
    WEB_PANEL_PASSWORD sent in a custom header, with lockout and a single-action lock.
  summary: No new dependency, same data and action boundary as the desktop panel.

alternatives:
  - Flask/FastAPI - more features, but a new dependency for three JSON endpoints.
  - Serve from the desktop app - only reachable while the Mac GUI runs.
  - Cookie sessions with CSRF tokens - more moving parts than a per-request header for one operator.

evidence:
  - id: source-project-regression-tests
    type: internal-evaluation

assumptions:
  - The panel is reachable only from the home LAN (no port forwarding on the router).
  - Plain HTTP on the LAN is acceptable; the password could be sniffed by a device on the same network.

consequences:
  positive:
    - Any phone or computer on the LAN can watch and act without installing the app.
    - Read-only by default when no password is configured.
  negative:
    - No TLS; Docker controls stay desktop-only.
    - The image now carries gui/src so the page can reuse the desktop translations (single source).

review:
  interval: 6 months
  next_review: 2027-04-16
  triggers:
    - the panel must be reachable from outside the LAN
    - more operators or roles are needed

affected_capabilities:
  - serve-web-panel

migration:
  required: false

rollback:
  available: true
  plan: Set WEB_PANEL_ENABLED=false (the program then exits) and remove the published port.
```
