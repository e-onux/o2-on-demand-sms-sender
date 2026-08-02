# Constraints

| Constraint | Type | Drives |
|---|---|---|
| The modem is reachable through its local Huawei HTTP API and requires credentials from the environment. | integration / security | ADR-0002 |
| The worker must run unattended and restart after failure or host reboot. | reliability | ADR-0003 |
| Docker worker and host desktop GUI need shared status without adding a database service. | architecture | ADR-0004 |
| Packaged desktop builds must target macOS, Windows and Linux from platform-native CI runners. | platform | ADR-0005 |
| macOS may restrict Documents access and background UI behavior. | platform / privacy | ADR-0005 |
| The operator's free renewal keyword and service number are `WEITER` and `80112`. | business | renew-highspeed-data |
| Real SMS sending and inbox deletion are destructive external actions and cannot be exercised by automated tests. | safety | execute-manual-modem-actions |
