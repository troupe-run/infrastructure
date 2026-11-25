# Proposal

## Why

`test_an_orphan_reparented_to_the_runs_init_is_reaped` is flaky (#407). It failed CI's check on Dependabot's #386 (ruff
0.17.5 → 0.17.6, tracked by #389), which has no ruff findings of its own. Its `ORPHAN` script polls
`/proc/<pid>/stat` until pid 1 reaps a killed orphan, and counts only `FileNotFoundError` as reaped. When the reap
lands between the `open` and the `read`, the read fails with `ESRCH` (`ProcessLookupError`), which escapes. The
script exits 1 although the orphan was reaped.

## What Changes

- The `ORPHAN` script's poll treats `ProcessLookupError`, and an empty read, as "reaped", like `FileNotFoundError`.
  A non-empty line it can't parse is still an error.
- The poll's read moves into a small function the test module also runs directly. New tests drive it with a stubbed
  `open` that raises `ProcessLookupError`, or returns an empty read. They fail without the fix and run on every OS,
  not only where the contained run can.

No spec changes: this fixes a test, not a behaviour of the workflow (`skip_specs: true`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

- `scripts/tests/test_mutation_workflows.py` only. No workflow, script or OpenTofu change, and no plan.
