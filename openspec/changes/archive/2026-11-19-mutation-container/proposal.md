# Proposal

## Why

troupe's weekly mutation run lost its hosted runner a fourth time (dry run 44469923116), with #341's session layers
live. So a mutant's own-group kill wasn't the only way. What's left is a mutant signalling every process the user
owns (`kill(-1, …)`), which crosses sessions and reaches the runner agent (same user), or real memory starvation (#345).
A probe (troupe-run/infra-probe-runner-killall, run 44480752897) showed both can be contained without losing the
runner. The owner chose (2026-11-19) the route that keeps the runner's own environment, in place of the issue's first
"Docker container" wording.

## What Changes

- **The mutation runs in its own PID namespace and cgroup.** Both mutate steps (`mutation.yml`, delivered
  `mutation-pr.yml`) run the mutation through one shell function: `sudo` (keeping the step's environment) →
  `systemd-run --scope` with `MemoryMax`, `MemorySwapMax=0` and `TasksMax` → `unshare --pid --fork --mount-proc
  --kill-child` → `setpriv` back to the runner's user. A `kill(-1)` inside reaches only the run's own processes, and
  exhaustion kills the run, not the runner. This replaces #341's `setsid --wait`. #341's per-mutant session stays, so
  one bad mutant still ends only itself.
- **The step says which it was.** After a non-zero exit, the step reads the kernel log since the run started and
  reports "out of memory" (with the limit) or "killed by a signal" / "exited with status N".
- The sampler and uploads stay in the step's shell, outside.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: the run's isolation covers a mutant signalling every process, and memory exhaustion.

## Impact

- `.github/workflows/mutation.yml`, `.github/workflows/mutation-pr.yml` (delivered), their tests, the docs. The plan
  updates troupe's `mutation-pr.yml`.
- After the apply: the troupe dry run.
