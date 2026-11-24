# Tasks

## 1. Keep the output's tail

- [x] 1.1 Tests first (`test_mutation_unreached.py`):
      - `run_command` with a `tail` streams every line through and keeps the last 50;
      - without one, it behaves as before;
      - a timeout still returns -1.
- [x] 1.2 `Run` takes an optional `tail`; `run_command` keeps it. The tests' recorders accept it.

## 2. Recognise the stop

- [x] 2.1 Tests first:
      - exit 1 with the sentence: every mutant reached by no test, modules finished, the run goes on to the next unit;
      - exit 1 without the sentence: `RunError`;
      - the sentence with exit 0 or 2: as before.
- [x] 2.2 `run_mutmut` recognises it (D2), with the sentence in one constant.
- [x] 2.3 `from_mutmut(unreached=True)` counts a `null` result as `no_tests` (D3).

## 3. Name it

- [x] 3.1 Tests first: the state record has `unreached`, the summary's state section shows its line, and the log names
      the unit.
- [x] 3.2 `UnitState.unreached`, `state_section` and the log line.

## 4. Docs and check

- [x] 4.1 `docs/development-workflow.md`, mutmut's limits: a unit whose unit tests reach none of its code is reported
      with every mutant reached by no test. The locator check's docstring lists the sentence to re-check on a mutmut
      upgrade.
- [x] 4.2 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-24).
