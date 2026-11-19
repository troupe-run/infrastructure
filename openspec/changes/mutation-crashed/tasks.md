# Tasks

## 1. The record (design D1)

- [ ] 1.1 Tests first in `test_mutation_report.py`:
      - a report with `crashed_mutants` round-trips;
      - a count that disagrees with the list is refused, naming the module and both numbers;
      - a missing list is refused;
      - a version 1 report is refused, naming the version.
- [ ] 1.2 `Crashed`, `Module.crashed_mutants`, the reader and writer, `VERSION = 2`; existing callers and fixtures follow

## 2. Collecting them (design D2)

- [ ] 2.1 Tests first:
      - `from_mutmut` on the real 3.8.1 fixture, with a mutant's code set to -9, lists it with its path, line, change
        and code;
      - `from_stryker` on the real 10.1.1 fixture lists a `RuntimeError` mutant, with no code;
      - `run_mutmut` maps a crashed path back to the unit's source.
- [ ] 2.2 Collect them in `from_mutmut`, `from_stryker` and `run_mutmut`

## 3. The summary (design D3)

- [ ] 3.1 Tests first in `test_mutation_issues.py`: the summary lists each crashed mutant (name, path:line, exit code,
      change) under the line saying it ended only its own test process; with none, there's no section
- [ ] 3.2 `summary()` lists them

## 4. Docs and verification

- [ ] 4.1 `docs/development-workflow.md`'s "Mutation testing": the summary names crashed mutants, and exclusions are the
      owner's
- [ ] 4.2 The full check passes (in the orchestrator's slot)

## Workflow follow-up

- Read the pull request's plan: troupe's `mutation_report.py` and `mutation_run.py` updated, nothing else.
- After the merge and apply: the troupe dry run; report its crashed mutants to the owner.
