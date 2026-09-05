# Technical Debt

Tracked deliberately, not discovered by accident. Each item links the capability/ADR it touches and the trigger
that should force action (often a budget breach).

| ID | Where | Description | Trigger to address | Severity |
|---|---|---|---|---|
| TD-001 | observe-service-status, operate-docker-service, manage-desktop-lifecycle | `gui/src/control_panel.py` combines rendering, Docker orchestration and desktop lifecycle in 1,547 lines. See RP-001. | Next structural GUI change or another regression caused by cross-responsibility coupling | high |
| TD-002 | ADR-0002, ADR-0005 | The original dependency/framework comparison is absent from repository history. | Dependency replacement, framework migration or next ADR review | medium |
