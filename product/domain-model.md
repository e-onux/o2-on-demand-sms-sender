# Domain Model

## Entities

- **Allowance cycle** - usage accumulated from a verified baseline until renewal; normally renewed after the
  configured threshold or an operator trigger.
- **Usage sample** - the modem's current daily byte counter plus capture time.
- **Operator trigger** - a received O2 SMS whose normalized text exactly matches a supported 80% or exhausted
  notification.
- **Renewal action** - a `WEITER` SMS sent to service number `80112`, with time, reason and result.
- **SMS message** - an incoming or outgoing modem message with box, index, timestamp and body.
- **Runtime snapshot** - current worker health, usage, baseline, daily SMS count and last action/error.
- **Event** - bounded append-only operational history displayed by the control panel.
- **Service state** - Docker Compose state and recent logs for the worker service.
- **Desktop preference** - language, close behavior and login-start behavior stored on the host.

## Relationships and rules

- One allowance cycle starts from one verified usage sample and can end in at most one successful renewal action.
- One operator trigger fingerprint can cause at most one renewal action.
- The daily SMS count is derived from successful renewal actions for the current local date.
- SMS retention keeps the newest configured count across incoming and outgoing boxes combined.
- A runtime snapshot references the newest event and action but event history remains bounded independently.
