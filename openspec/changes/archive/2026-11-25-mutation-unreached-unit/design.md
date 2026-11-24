# Design

## Context

mutmut 3.8.1's `run_stats_collection` prints "Stopping early, because we could not find any test case for any
mutant. It seems that the selected tests do not cover any code that we mutated." and calls `exit(1)`. It does that
when the stats pass succeeds, but no test is associated with any mutated function. It saves no stats. The `.meta`
files from generating the mutants are already written, with every result `null`.

A unit whose tests fail in the copy also exits 1 with no stats. So the two can't be told apart from the files, only
from the output. `run_command` streams the output to the job's log and keeps none of it.

## Goals / Non-Goals

**Goals:**

- Report such a unit honestly: every mutant reached by no test.
- Judge it.
- Carry on to the next unit.
- Recognise only that stop.

**Non-Goals:**

- mutmut's other early stop, "tests recorded trampoline hits but none for the mutated functions"
  (`_check_test_to_mutant_associations`). It wasn't seen, and the owner asked for this stop exactly. It still fails the
  run, and gets its own issue if it shows up.
- Writing tests for `troupe-vcs-git`. That's troupe's work, which the module issues will ask for.

## Decisions

### D1: Keep the output's tail, not a file

`Run` gains an optional keyword `tail: list[str] | None`. `run_command` then reads the command's combined output line
by line, writes each line through to its own stdout (so the log is unchanged), and keeps the last 50 lines in `tail`.
Without `tail`, it runs as now. Only `run_mutmut`'s `mutmut run` passes one. The tests' recorders accept the keyword,
and the ones for this case fill it.

### D2: The exact match

The stop is recognised when both hold:

- the exit code is 1;
- a line of `tail`, stripped of the spinner's carriage returns and whitespace, starts with the exact sentence `Stopping
  early, because we could not find any test case for any mutant.`.

Either alone is the failure it was before: `RunError`, which names the unit. The sentence is held in one constant, with
the mutmut version it comes from. A version change in `scripts/mutation.json` is already checked by the locator check
(#377), whose docstring adds this sentence to what to re-check.

### D3: Every mutant reached by no test, from the .meta files

`mutation_report.from_mutmut` gains `unreached: bool = False`. When it's true, a `null` result counts as `no_tests`
(mutmut's own status for a mutant no test reaches) instead of making the module unfinished. Every module is then
finished, its score is 0, and the issue logic judges it as for any module.

A non-null result still counts as it is. A `.meta` file can hold results from an earlier run whose selection reached
the code, but the state's fit check (#394) discards those when the selection changes, so in practice all are `null`.

### D4: Named in the state record and the log

`UnitState` gains `unreached: bool`. The summary's state section adds a line under the unit: "its selected tests reach
none of its code: every mutant counted as reached by no test". `read_state` already accepts any unit fields.

`run_mutmut` also logs `mutation_run: <unit>: its selected tests reach none of its code; every mutant counted as reached
by no test`, so a pull request's report, which keeps no state, says it too.

## Risks / Trade-offs

- **[mutmut rewords the sentence in a later version]** → the stop is a failed run again, as today: safe, and visible.
  Re-checking it is on the locator check's list.
- **[A unit's modules all score 0 and raise issues]** → that's the intended signal (#394). `max_new_issues` (5) bounds
  each run.
