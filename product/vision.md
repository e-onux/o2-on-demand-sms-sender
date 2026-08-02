# Product Vision

## Problem

An O2 prepaid data user must request the next free high-speed allowance by SMS whenever the current allowance
is nearly or fully consumed. Manual monitoring is repetitive, easy to miss and difficult to diagnose over long
periods.

## Outcome

The service renews the allowance reliably, records why and when it acted, bounds its long-running state, and
gives the operator a localized desktop control panel for status, Docker lifecycle and explicit manual actions.

## Principles

- Prefer verified modem state over heuristics or formatted display values.
- Make every automated or manual SMS observable and attributable.
- Keep destructive operations explicit, confirmed and testable without touching a real modem.
- Remain recoverable and bounded during months or years of unattended operation.
