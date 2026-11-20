# Proposal

## Why

#367 (#368) records each mutmut process's memory peaks so #366 can set a per-mutant cap from them. The measuring
dry run 44673717060 hit the runaway mutant as expected (the 12G cgroup's OOM kill, a 5.1 GB process), but logged no
`memory:` lines (#371). `mutation_run.py`, which printed the summary in `run_mutmut`'s `finally`, runs inside the same
cgroup, so the kill ended it too, and the peaks file sat in the checkout, which isn't uploaded. The peaks are lost
exactly when they matter, and #366's second pull request has nothing to set its default from.

## What Changes

- **The peaks go where the job keeps them.** Both workflows name a peaks file, `out/peaks-<repository>.log`
  (`out/peaks-pr.log` for the pull request run), in a `PEAKS` variable beside `RESOURCES`, and upload it even when
  the run fails. `run_mutmut` records into it, marking where each unit starts, and leaves it in place.
- **The summary is printed from outside the run.** The mutate step's exit trap, which runs outside the cgroup, prints
  the `memory:` lines from that file through `mutation_run.py peaks`. A run killed by its cgroup still gets its
  summary. A local run with no `PEAKS` prints its own, as today.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a run's `memory:` summary survives the run being killed.

## Impact

- `scripts/mutation_run.py` (delivered to troupe), `.github/workflows/mutation.yml`,
  `.github/workflows/mutation-pr.yml` (delivered to troupe), and their tests.
- `docs/development-workflow.md`, "Mutation testing".
- The plan updates troupe's delivered `mutation_run.py` and `mutation-pr.yml`.
