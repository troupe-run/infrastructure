# Proposal

## Why

Owner decision (2026-11-20, #361): the troupe dry-run report lists every crashed mutant, with its file, line and
mutation and what it ended, so the owner can decide on any `# pragma: no mutate` exclusions from real data. No
exclusions without the owner, and the containment (#341, #345, #347) stays either way. Today
`scripts/mutation_report.py` keeps details for survivors only: a crashed mutant is a count.

## What Changes

- **A crashed mutant is recorded like a survivor:** its name, path, line and change, plus mutmut's exit code (none
  for Stryker, which reports a crash without one). Each module's `crashed_mutants` list is held to its `crashed`
  count by the strict reader, and the report's version becomes 2.
- **Both tools' readers collect them** (`from_mutmut`, `from_stryker`), and `mutation_run` maps their paths back to
  the repository, as it does survivors'.
- **The weekly run's summary lists them,** saying what each ended. A crash in the report ended only its own test
  process: mutmut recorded it and went on. A crash that ended the run doesn't reach the report; it shows as the
  unit's failure in the step (#345's messages).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a run's report and summary name its crashed mutants.

## Impact

- `scripts/mutation_report.py`, `scripts/mutation_run.py` (both delivered), `scripts/mutation_issues.py`, and their
  tests. The plan updates troupe's delivered `mutation_report.py` and `mutation_run.py`.
- After the apply: the troupe dry run names its crashed mutants.
