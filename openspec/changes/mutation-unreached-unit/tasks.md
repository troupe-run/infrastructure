# Tasks

## 1. Keep the output's tail

- [ ] 1.1 Tests first (`test_mutation_unreached.py`):
      - `run_command` with a `tail` streams every line through and keeps the last 50;
      - without one, it behaves as before;
      - a timeout still returns -1.
- [ ] 1.2 `Run` takes an optional `tail`; `run_command` keeps it. The tests' recorders accept it.

## 2. Recognise the stop

- [ ] 2.1 Tests first:
      - exit 1 with the sentence: every mutant reached by no test, modules finished, the run goes on to the next unit;
      - exit 1 without the sentence: `RunError`;
      - the sentence with exit 0 or 2: as before.
- [ ] 2.2 `run_mutmut` recognises it (D2), with the sentence in one constant.
- [ ] 2.3 `from_mutmut(unreached=True)` counts a `null` result as `no_tests` (D3).

## 3. Name it

- [ ] 3.1 Tests first: the state record has `unreached`, the summary's state section shows its line, and the log names
      the unit.
- [ ] 3.2 `UnitState.unreached`, `state_section` and the log line.

## 4. Docs and check

- [ ] 4.1 `docs/development-workflow.md`, mutmut's limits: a unit whose unit tests reach none of its code is reported
      with every mutant reached by no test. The locator check's docstring lists the sentence to re-check on a mutmut
      upgrade.
- [ ] 4.2 The full check passes (in the orchestrator's slot).
