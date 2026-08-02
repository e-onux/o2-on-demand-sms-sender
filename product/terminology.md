# Terminology

Ubiquitous language for this project. One term, one meaning. Capabilities, code and docs use these words.

| Term | Meaning | Not to be confused with |
|---|---|---|
| Daily counter | Raw bytes reported by the modem for the current local day | The allowance-cycle usage |
| Baseline | Verified daily-counter value at the start of an allowance cycle | A hard-coded 2 GiB amount |
| Cycle usage | Non-negative difference between current daily counter and baseline | Total modem traffic history |
| Renewal trigger | Threshold crossing or exact supported O2 notification | Any SMS containing a keyword |
| Renewal action | Successful `WEITER` SMS to `80112` | Receiving an O2 notification |
| Message fingerprint | Stable identifier used to suppress duplicate trigger handling | Modem message index alone |
| Runtime snapshot | Latest atomic JSON status exposed to the GUI | Docker logs |
| Event history | Bounded JSONL operational records | Modem SMS storage |
| Control panel | Host desktop GUI | Docker worker process |
| Tray helper | macOS UIElement process that owns the menu-bar icon | Main Tkinter window |
