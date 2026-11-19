# Tasks

## 1. The record (design D1)

- [x] 1.1 Tests first in `test_mutation_report.py`:
      - a report with `crashed_mutants` round-trips;
      - a count that disagrees with the list is refused, naming the module and both numbers;
      - a missing list is refused;
      - a version 1 report is refused, naming the version.
- [x] 1.2 `Crashed`, `Module.crashed_mutants`, the reader and writer, `VERSION = 2`; existing callers and fixtures follow

## 2. Collecting them (design D2)

- [x] 2.1 Tests first:
      - `from_mutmut` on the test tree shaped as mutmut 3.8.1 writes it, with a mutant's code set to -11, lists it with
        its path, line, change and code;
      - `from_stryker` on a report shaped as Stryker 10.1.1 writes it lists a `RuntimeError` mutant, with no code;
      - `run_mutmut` maps a crashed path back to the unit's source.
- [x] 2.2 Collect them in `from_mutmut`, `from_stryker` and `run_mutmut`

## 3. The summary (design D3)

- [x] 3.1 Tests first in `test_mutation_issues.py`: the summary lists each crashed mutant (name, path:line, exit code,
      change) under the line saying it ended only its own test process; with none, there's no section
- [x] 3.2 `summary()` lists them

## 4. Docs and verification

- [x] 4.1 `docs/development-workflow.md`'s "Mutation testing": the summary names crashed mutants, and exclusions are the
      owner's
- [x] 4.2 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-20)

## 5. The host's account of how a run ended (design D4)

- [x] 5.1 Tests first in `test_mutation_workflows.py`: with a stand-in sudo printing a journal, the exit trap keeps only
      the OOM, oomd and unit-stop lines, saves them to `journal-troupe.log` and the log; with no readable journal it
      saves nothing; the pull request run uploads `journal-pr.log` with its readings
- [x] 5.2 Both workflows' sampler block: the start time, and the capture in its exit trap; the journal file is never the
      readings file
- [x] 5.3 The full check passes (in the orchestrator's slot)

## Workflow follow-up

- Read the pull request's plan: troupe's `mutation_report.py` and `mutation_run.py` updated, nothing else.
- After the merge and apply: the troupe dry run; report its crashed mutants to the owner.
