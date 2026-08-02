# ADR-0002: Use huawei-lte-api for modem access

```yaml
id: ADR-0002
title: Use huawei-lte-api for modem access
status: under-review
date: 2026-08-02

context:
  description: >
    The worker and manual action command must authenticate to a Huawei LTE modem, read traffic and SMS data,
    delete SMS messages, reset the modem traffic counter and send the O2 renewal SMS.

decision:
  selected: Use Python and huawei-lte-api as the single adapter for Huawei modem HTTP operations.
  summary: Keep credentials in environment variables and keep modem calls out of GUI rendering code.

alternatives:
  - Call the modem HTTP endpoints directly with a generic HTTP client.
  - Use browser automation against the modem administration interface.
  - Use a different Huawei modem SDK.

evidence:
  - id: source-huawei-lte-api
    type: official-documentation
  - id: source-project-regression-tests
    type: internal-evaluation

assumptions:
  - The deployed modem remains compatible with the API implemented by huawei-lte-api.
  - The modem is reachable from the worker over the local network.
  - Environment-provided credentials remain the accepted authentication mechanism.

consequences:
  positive:
    - Modem authentication, SMS and traffic calls use one established adapter.
    - Tests can replace the adapter with deterministic fake clients.
  negative:
    - Reliability depends on modem firmware compatibility and third-party package maintenance.
    - The historical comparison that originally selected this dependency is not recorded.

review:
  interval: 6 months
  next_review: 2027-02-02
  triggers:
    - modem firmware or endpoint behavior changes
    - huawei-lte-api becomes unmaintained or reports a security issue
    - a supported modem cannot complete a contracted action

affected_capabilities:
  - renew-highspeed-data
  - retain-recent-sms
  - execute-manual-modem-actions

migration:
  required: false

rollback:
  available: true
  plan: Pin the last verified dependency version or replace the adapter behind the existing action boundaries.
```

## Review note

This brownfield ADR records the current architecture. It remains under review because the original alternative
evaluation is not available in repository history.
