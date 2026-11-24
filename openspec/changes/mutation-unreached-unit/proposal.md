# Proposal

## Why

Since #394, mutation runs use only each unit's unit tests. When a unit's unit tests reach none of its code, mutmut
3.8.1 stops after its stats pass ("Stopping early, because we could not find any test case for any mutant") and exits
1. `run_mutmut` takes exit 1 as a failed run. So the repository's run stops at that unit, and the units after it are
never reached, so the fill can never finish. troupe's `troupe-vcs-git` does this today: its 2 unit tests reach none of
its 5 source files (#398's trial). Owner decision (2026-11-24, #399): option A.

## What Changes

- `run_command` keeps the last lines of a command's output when asked, still streaming all of it to the log. `Run`
  gains that optional `tail`.
- `run_mutmut` recognises mutmut's own stop exactly: exit 1 and that sentence on a line of its output. The unit's
  modules are then read from the `.meta` files mutmut wrote while generating, with every mutant reached by no test.
  They are finished and judged, at a score of 0, so their issues ask for unit tests. The run carries on to the next
  unit.
- The unit's state record notes it ("its selected tests reach none of its code: every mutant counted as reached by no
  test"), and the summary's state section shows it under the unit. The log names it on every run, pull requests' too.
- Any other mutmut failure still fails the run, as before. So does exit 1 without that sentence, and the sentence
  without exit 1.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a unit whose selected tests reach none of its code is reported and judged, not a failed run.

## Impact

- `scripts/mutation_run.py`, `scripts/mutation_report.py` and `scripts/mutation_state.py`, all delivered to troupe,
  with their tests. The new tests go in `scripts/tests/test_mutation_unreached.py`, since `test_mutation_run.py` is at
  the size gate.
- `docs/development-workflow.md`.
- The plan updates troupe's delivered copies of the three scripts.
