## Context

#367's design D3 had `run_mutmut` print the `memory:` lines in its `finally` and keep the peaks file in mutmut's
working directory. In CI, `mutation_run.py` runs inside `run_contained`'s cgroup (#345), so the cgroup's OOM kill
(dry run 44673717060) ended it before its `finally`, and the checkout isn't uploaded. The step's shell, its sampler
and its exit trap run outside the cgroup: that's where #361 D4's journal lines come from, and they survived the same
kill.

## Goals / Non-Goals

**Goals:** the peaks and their summary survive any end of the run; one summary per unit, as before.

**Non-Goals:** recording the peak of a process the kernel kills (it can't write); setting the cap (#366).

## Decisions

### D1. The workflows name the peaks file; the run records into it

Both mutate steps set `PEAKS` (`$GITHUB_WORKSPACE/out/peaks-<repository>.log`; `.../out/peaks-pr.log`) beside
`RESOURCES`. `run_contained` carries the step's environment into the run (#345). With `PEAKS` set, `run_mutmut`
hands that path to the plugin, appends `unit <name>` before each unit's run, and neither prints nor deletes it. The
weekly job uploads `out/` already; the pull request run's resources upload gains `out/peaks-pr.log`. With no `PEAKS`
(a local run), the working-directory file and the run's own `memory:` lines stay as they are.

### D2. The exit trap prints the summary

The sampler block's exit trap, the same in both workflows (a test holds them equal), runs
`python3 "$MUTATION_SCRIPTS/mutation_run.py" peaks "$PEAKS"` when the file isn't empty. Each workflow sets
`MUTATION_SCRIPTS` to where its copy of the scripts is (`infra/scripts` in the weekly run, `scripts` in the pull request
run), so the block itself stays identical. `mutation_run.py peaks` splits the file at its `unit` lines and prints
`memory_lines` for each. Lines before any `unit` line are summarised under `?`. A failure there never fails the trap
(`|| true`): the summary must not change how the step ends.

## Risks / Trade-offs

- `python3` must be on the runner outside `uv` → GitHub's Ubuntu images carry it, and the weekly run already uses it
  (`run_contained python3 ...`).
- A unit marker written by a run killed mid-unit still heads that unit's lines → the summary covers what was recorded
  before the kill, which is what's wanted.
