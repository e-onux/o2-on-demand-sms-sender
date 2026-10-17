# ADR-0008: Use the default bridge network instead of host networking

```yaml
id: ADR-0008
title: Use the default bridge network instead of host networking
status: accepted
date: 2026-10-17
supersedes: ADR-0003 (networking part only; Compose and supervisord stay)

context:
  description: >
    ADR-0003 chose host networking. Its review trigger "host networking prevents supported-platform operation"
    fired: Docker Desktop on macOS and Windows supports host networking only from 4.34, after signing in and
    enabling it in Settings > Resources > Network, and containers then cannot bind to the host's addresses.
    The operator's own deployment already runs on a bridge network and reaches the modem through NAT.

decision:
  selected: Drop network_mode host from the published docker-compose.yml and publish the web panel port.
  summary: One Compose file works unchanged on Linux, macOS and Windows.

alternatives:
  - Keep host networking and document the Docker Desktop setting - an extra, account-bound setup step.
  - Ship two Compose files - two paths to keep working.

evidence:
  - id: source-docker-host-network
    type: official-documentation
  - id: source-project-regression-tests
    type: internal-evaluation

assumptions:
  - The modem is reachable from the Docker host's network (true for a LAN modem behind NAT).
  - No feature needs the host's own interfaces; the modem-latency ping already runs from a bridge container in
    the operator's deployment.

consequences:
  positive:
    - The quick start needs no Docker settings on any platform.
    - The web panel is reachable through a normal published port.
  negative:
    - Modem latency includes a NAT hop of well under a millisecond.

review:
  interval: 12 months
  next_review: 2027-10-17
  triggers:
    - a feature needs the host network namespace
    - a modem is reachable only from the host interface

affected_capabilities:
  - operate-docker-service
  - serve-web-panel

migration:
  required: false

rollback:
  available: true
  plan: Restore network_mode host in docker-compose.yml and remove the ports section.
```
