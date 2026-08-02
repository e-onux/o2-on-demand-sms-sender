# Testing Strategy

Trellis derives tests from contracts. Test types:

- **Unit** - internal logic of a capability.
- **Contract** - the declared input/output contract holds.
- **Property-based** - invariants hold across the input space (e.g. "price never negative").
- **Regression** - previously-passing scenarios still pass.
- **Integration** - interaction with other capabilities/services.
- **Visual** - rendered output matches expectation (frontend).
- **Security** - authz, input validation, data access.
- **Performance** - latency/throughput/memory budgets.
- **User validation** - a human confirms the output is correct *for the business* (cockpit).

Which are mandatory is set by your profile (see the profiles at https://github.com/e-onux/trellis/tree/main/standard/profiles) and recorded per capability in
`contract.yaml → verification`.

## Project test layers

- `tests/test_worker_usage.py` verifies byte parsing, ISO/legacy dates, threshold renewals, exact operator
  triggers, baseline resets, idempotency and bounded SMS retention with fake clients.
- `tests/test_runtime_status.py` verifies atomic state updates, daily rollover, bounded event history and locking.
- `tests/test_runtime_status.py` also verifies status interpretation, localized formatting, tray visibility and
  startup command construction without changing the host.
- CI runs the entire unittest suite and Trellis audit on every relevant push and pull request.

Real modem operations remain a user-validation step. Automated tests must not send SMS, delete messages,
start or stop the user's Docker service, change login items or require GUI interaction.

## Regression command

```sh
python -m unittest discover -s tests -v
```
