# ADR-0003: Run the worker with Docker Compose and supervisord

```yaml
id: ADR-0003
title: Run the worker with Docker Compose and supervisord
status: accepted
date: 2026-08-02

context:
  description: >
    Renewal monitoring must stay active for months, recover after process failure and be controllable from a
    desktop GUI without requiring the operator to remember container commands.

decision:
  selected: Package the worker in Docker Compose, supervise it with supervisord and use host networking where supported.
  summary: Docker owns deployment and restart behavior; the GUI invokes explicit Compose lifecycle commands.

alternatives:
  - Run the worker directly as a host login service.
  - Run a periodic cron or task-scheduler job.
  - Embed the worker loop in the desktop GUI process.

evidence:
  - id: source-docker-compose
    type: official-documentation
  - id: source-project-regression-tests
    type: internal-evaluation

assumptions:
  - Docker Compose is installed and available to the logged-in operator.
  - The container can reach the modem on the host network.
  - The desktop GUI may be closed without stopping the automation worker.

consequences:
  positive:
    - The worker lifecycle is isolated from the desktop window lifecycle.
    - Compose and supervisord provide repeatable startup and restart behavior.
  negative:
    - Desktop use depends on Docker being installed and running.
    - Host networking and Docker executable discovery vary by operating system.

review:
  interval: 12 months
  next_review: 2027-08-02
  triggers:
    - Docker is no longer a supported deployment target
    - the worker fails to restart after process or host failure
    - host networking prevents supported-platform operation

affected_capabilities:
  - renew-highspeed-data
  - retain-recent-sms
  - operate-docker-service
  - observe-service-status

migration:
  required: false

rollback:
  available: true
  plan: Run the worker CLI directly with the documented environment and preserve the shared data directory.
```
