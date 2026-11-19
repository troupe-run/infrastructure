# Design

## Context

The probe (#341's comment; troupe-run/infra-probe-runner-pgkill, run 44455124559):

- `Runner.Listener` (2216), `Runner.Worker` (2236) and a step's `bash` (2252) all had process group 2159. A step
  doesn't start a group of its own, so everything it starts inherits the runner agent's group.
- `kill -9 0` in a plain step: the step stayed "in progress" and the job was lost, as in #337's three dry runs.
- `setsid --wait bash -c '...; kill -9 0'`: only the inner session (group 2283) died, with exit 137. The step went on,
  and the next step ran.

mutmut 3.8.1 forks one child per mutant and runs pytest in it, which loads `_mutation_children_plugin` (the delivered
`scripts/mutation_children.py`). Our report maps mutmut's exit code `-9` to "crashed" (`mutation_report.py`).

## Decisions

### D1. Each mutant's test process calls `os.setsid()` (the containment that lets the run go on)

In the plugin's `pytest_configure`, when `MUTANT_UNDER_TEST` names a mutant (not empty, `stats`, `fail` or
`list_all_tests`, which run in mutmut's own process) and the platform has `os.setsid`, the process becomes the leader
of a new session. A forked child is never already a group leader, so `setsid` succeeds there. A mutant that kills its
own group then kills only that child: mutmut sees exit -9, records it, and starts the next mutant. Without D1, D2
alone would let one such mutant kill the whole run every week.

### D2. The run is under `setsid --wait` (the backstop that keeps the runner alive)

Both mutate steps prefix the run with `setsid --wait`. Anything that escapes D1, such as a kill from mutmut's own
process or the stats pass, ends the session and fails the step with its status. It never reaches the runner agent.
The sampler (#337) stays in the step's shell, outside the session, so it keeps writing and reports at the end.
`--wait` makes the step wait for the run and return its exit status, as it does now.

### D3. Tests

- The plugin: a real POSIX test forks a process that runs the plugin's hook with a mutant named, then kills its own
  group. The parent survives and sees the child's -9. With no mutant named (`stats`), the hook leaves the session
  alone.
- The workflows: both steps' run lines start with `setsid --wait`. The sampler block is outside it, and the step
  still ends with the run's exit status. One step script runs with `bash` and a stand-in run that does `kill -9 0`:
  the step's shell survives and reports the failure.

## Risks / Trade-offs

- **A test in troupe that relies on sharing the runner's session** (a terminal, or job control) → none known. Tests
  that start their own sessions still can. The troupe dry run checks this.
- **`setsid` isn't on macOS or Windows** → both workflows run on `ubuntu-latest` only. The plugin checks
  `hasattr(os, "setsid")`.

## Migration Plan

Merge and apply (troupe's `mutation-pr.yml` and `mutation_children.py` change), then dry-run troupe in CI. Report
the scores, the runtime, the lowest free memory, and any crashed mutants. Then #339.
