# Proposal

## Why

The troupe dry run after #345 ran contained as designed: the runner survived and the readings arrived (lowest free
memory 14,588 MB). It failed in mutmut's baseline stats run, though (#347). troupe's
`test_killing_a_child_also_kills_the_grandchild_it_started` saw its killed grandchild as still running.
`run_contained` execs down to the command, so `mutation_run.py` is pid 1 of its PID namespace. Orphans reparent to
pid 1, and Python doesn't reap them, so the grandchild stays a zombie. troupe's `is_running` counts zombies, a
documented limit. Outside a namespace systemd reaps them, which is why troupe's own CI passes.

## What Changes

- **A reaping init.** In `run_contained`, the `bash` that restores the step's environment no longer `exec`s the
  command. It runs it as a child and `wait`s for it, staying pid 1 of the namespace. Bash reaps every child it gets,
  orphans reparented to it included, so nothing is left a zombie. Its exit status is the command's, plain or by
  signal, so the step's report is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: the contained run reaps its orphans, as an init does.

## Impact

- `.github/workflows/mutation.yml`, `.github/workflows/mutation-pr.yml` (delivered), and their tests. The plan updates
  troupe's `mutation-pr.yml`.
- After the apply: the troupe dry run; then #339.
