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
- **A step keeps the host's account of how it ended** (design D4, folded in by the orchestrator, 2026-11-20): dry
  run 44633465646 ended with SIGTERM to the step's own shell and nothing recorded the sender. Each mutate step's exit
  trap now saves, since the step began, the journal lines from the sources that can name one (the kernel's OOM lines,
  systemd-oomd, and systemd on the runner's service or the run's own scope), to the log and to
  `journal-<repository>.log`, uploaded with the readings.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a run's report and summary name its crashed mutants, and a run keeps the host's account of how
  it ended.

## Impact

- `scripts/mutation_report.py`, `scripts/mutation_run.py` (both delivered), `scripts/mutation_issues.py`, and their
  tests. `.github/workflows/mutation.yml` and `.github/workflows/mutation-pr.yml` (delivered), and
  `scripts/tests/test_mutation_workflows.py`. The plan updates troupe's delivered `mutation_report.py`,
  `mutation_run.py` and `mutation-pr.yml`.
- `docs/development-workflow.md`, "Mutation testing".
- After the apply: the troupe dry run names its crashed mutants, and who ended it if the host did.
