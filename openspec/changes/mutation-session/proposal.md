# Proposal

## Why

troupe's weekly mutation run lost its hosted runner three times (#337's dry runs; #341). A probe in
troupe-run/infra-probe-runner-pgkill (run 44455124559) found why. A step's shell is in the same process group as the
runner's `Runner.Listener` and `Runner.Worker`, so `kill -9 0` from a step kills the runner agent: the job hangs, then
is lost, with no log. Under `setsid --wait` the same kill ends only its own session, and the job carries on. troupe's
`platform/processes.py` kills process groups (`os.killpg`) and probes pids (`os.kill(pid, 0)`), so a mutant that
points either at the caller's own group can do exactly that.

## What Changes

- **Each mutant's tests run in a session of their own.** The children plugin mutmut loads calls `os.setsid()` in a
  mutant's test process, so a mutant that kills its own process group ends only itself. mutmut then records it as a
  kill by signal ("crashed" in the report), and the run goes on to the next mutant.
- **The mutation runs in a session of its own.** Both mutate steps (`mutation.yml`'s Mutate, the delivered
  `mutation-pr.yml`'s) run `mutation_run.py` / `mutation_pr.py` under `setsid --wait`, so nothing the run starts can
  signal the runner agent. The step's own shell, its resource sampler and its upload stay outside it: a run that
  dies still fails the step normally, and keeps its log and readings.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a mutant can't stop the runner, and can't stop the rest of the run.

## Impact

- `scripts/mutation_children.py` (delivered), `.github/workflows/mutation.yml`, `.github/workflows/mutation-pr.yml`
  (delivered), their tests, the docs' "Mutation testing" section. The plan updates troupe's two delivered files.
- After the apply: a troupe dry run, then #339.
