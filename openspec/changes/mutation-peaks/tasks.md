# Tasks

## 1. Recording into the job's file (design D1)

- [ ] 1.1 Tests first in `test_mutation_run.py`:
      - with `PEAKS` set, `run_mutmut` hands the plugin that path, appends `unit <name>`, prints no `memory:` lines
        and leaves the file;
      - without it, today's behaviour holds (working-directory file, its own summary, removed after).
- [ ] 1.2 `run_mutmut` reads `PEAKS`

## 2. The summary from outside the run (design D2)

- [ ] 2.1 Tests first:
      - `mutation_run.py peaks <file>` prints each unit's `memory:` lines, split at its `unit` lines (and `?` for lines
        before any), and that no peaks were recorded for an empty or missing file;
      - in `test_mutation_workflows.py`, the sampler block's exit trap, with a peaks file written by a process that
        was then SIGKILLed, prints the `memory:` lines; with no `PEAKS` or an empty file it prints none and ends
        cleanly;
      - both mutate steps set `PEAKS` and `MUTATION_SCRIPTS`, and the pull request run uploads `out/peaks-pr.log`.
- [ ] 2.2 `mutation_run.py peaks`, the trap's line in both sampler blocks, and the steps' `PEAKS`/`MUTATION_SCRIPTS`

## 3. Docs and the check

- [ ] 3.1 `docs/development-workflow.md`: the peaks file and where the summary comes from
- [ ] 3.2 The full check passes (in the orchestrator's slot)

After the apply, a troupe dry run is to log the `memory:` lines: that's the measurement #366's second pull request
sets its default from.
