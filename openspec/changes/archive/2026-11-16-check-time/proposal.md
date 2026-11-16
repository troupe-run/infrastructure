# Proposal: check-time

## Why

The guard stops a commit's check after 600 s, and this repository's full check takes about 565 s, nearly all of it the
tests (#310). Several sessions share one machine, so under ordinary load the check passes 600 s and the commit is
refused (#305 and #307 were each stopped, some more than once), though nothing is wrong. A change to `oob/` alone runs
the full check too, because no scope covers `oob/`.

Measured on 2026-11-16 (10-core Mac, load 10–20): the suite took 564 s in one process at 49% CPU. It's a long tail of
about 3,200 tests that each start git or Python subprocesses; no test takes more than 18 s, and the five slowest files
take 440 s between them. The same suite with 4 xdist workers took 181 s. `tofu init` took 7.6 s in a worktree with no
`.terraform` and 0.4 s after it; `tofu validate` takes about 3 s.

## What Changes

- `scripts/check.py` runs the tests in parallel worker processes (pytest-xdist, already a dev dependency, and already
  supported by `guard_pytest`'s tag check). The worker count is a named setting in `check.py`, small enough for a
  shared machine (4, or fewer where the machine has fewer CPUs), not `auto`. The full check then takes about a third
  of the commit limit, and the same speed-up reaches CI's `check` job, which runs the same script.
- `scripts/check-paths.toml` declares an `oob` scope for `oob/**`, and the tests that read those files carry its tag,
  so a commit or pull request changing only `oob/` runs the tests that read it, not the whole suite.
- CI still runs the full check whenever the changed paths need it, as now; nothing in the guard or the 600 s limit
  changes.

Not changed, and why (design): the guard's 600 s limit and its message (they're in `guard.py`, which is delivered to
troupe and website, and the limit is no longer close once the tests run in parallel); skipping the `tofu` gates in a
scoped check (the development-workflow spec says a scope narrows only the tests, for every repository, and they cost
under 4 s once `tofu init` has run in a worktree); rewriting individual slow tests (no single test dominates).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: "A change runs the checks its paths need" adds the `oob/` declarations to the scopes this repository
  declares; a new requirement says this repository's check runs its tests in a named number of parallel workers.

## Impact

- `scripts/check.py` and its tests (`scripts/tests/test_check.py`).
- `scripts/check-paths.toml`, and the `oob` tag on the tests that read `oob/` (found by `guard_pytest`'s tag check).
- Load: a commit's check briefly uses up to 4 cores instead of 1, for about a third as long.
- No delivered file changes, so no delivery to troupe or website and no plan beyond the usual no-op.
