# Design: check-time

## Context

`scripts/check.py` runs seven gates in order; the guard's `commit-checks` runs it (or `--scope <name>...` of it, by
`scripts/check-paths.toml`) before each commit and stops it after `CHECK_TIMEOUT_SECONDS` (600 s, in `guard.py`). CI's
`check` job runs the same script with the guard's `check-scope` answer.

Where the time goes, measured on 2026-11-16 on the shared 10-core Mac with load averages of 10–20, from this branch's
base (`535a070`):

| Step | Time |
|---|---|
| tests, one process (`uv run pytest`) | 564 s (136 s user, 146 s system: 49% CPU) |
| tests, `-n 4` | 181 s (load rose to 44 during it, 4 of which were this run) |
| `tofu init`, no `.terraform` yet | 7.6 s (the issue saw 44 s on a slower network) |
| `tofu init`, after that | 0.4 s |
| `tofu validate` | about 3 s |
| ruff, mypy, `tofu fmt` | under 1 s each |

By file, the tests' time (summed over workers) is a long tail: `test_guard_pytest.py` 143 s, `test_guard_dependabot.py`
104 s, `test_claude_review_workflow.py` 97 s (522 tests), `test_guard_push_and_ci.py` 47 s, `test_guard_git_hooks.py`
31 s, `test_main_ci.py` 30 s, the rest under 20 s each. The slowest single test is 18 s; most of the slow ones take
1–4 s because they build git repositories or run the guard in a subprocess. The wall time is twice the CPU time, so a
serial run spends half of it waiting on process start-up and the disk, which is what parallel workers overlap.

## Goals / Non-Goals

**Goals:**
- The full check finishes well under the commit limit on a loaded machine: about a third of it, not 95%.
- A commit touching only `docs/` or `oob/` runs a scoped check that takes a small fraction of the limit.
- CI runs the full check whenever it does today, with the same gates and tests.

**Non-Goals:**
- Changing the guard (`guard.py`, its 600 s limit, its timeout message). It's delivered to troupe and website.
- Changing which gates a scope runs (the development-workflow spec's "A scope narrows only the tests").
- Speeding up individual tests, or the guard-tests legs in CI (they run `pytest` directly, not `check.py`).

## Decisions

### D1. The check's tests run under xdist with a named, small worker count

`check.py` adds `-n <workers>` to its pytest command, where `TEST_WORKERS = 4` is a named constant in `check.py` and the
count used is `min(TEST_WORKERS, os.cpu_count() or 1)`. pytest-xdist is already a dev dependency, and `guard_pytest`
already supports it: its tag check and its scope selection give the same result in workers as in one process
(development-workflow, "Tests run in parallel"; `test_guard_pytest.py` runs both ways).

- **Why 4, not `auto`:** the machine is shared by many sessions, and `auto` would take all 10 cores for every commit.
  4 cut the suite from 564 s to 181 s; the gain past 4 is smaller, since the run is half waiting already, and costs
  everyone else. 4 is also the vCPU count of GitHub's standard Linux and Windows runners, so CI gets the same speed-up
  without oversubscribing.
- **Why in `check.py`, not `addopts`:** `addopts` would also parallelise every `uv run pytest` a person runs by hand,
  the guard-tests legs in CI, and the nested pytest runs some tests make, which then spawn workers of their own.
  Putting it in the check limits it to the gate whose time the guard limits.
- **Alternatives:** `--dist loadfile` or `loadgroup` (keeps a file's tests together; no need, since every test passed
  under the default `load`); `-n auto` (rejected above); rewriting the slowest tests (no single one is worth it, and
  each rewrite risks the behaviour it checks).

pytest exits 5 when a scope selects no tests; xdist keeps that exit code, so `check.py`'s "nothing to test" handling is
unchanged. A test proves it with a scope nothing is tagged with.

### D2. An `oob` scope for `oob/**`

`scripts/check-paths.toml` gains `[scopes.oob] paths = ["oob/**"]`. The tests that read files under `oob/` get
`@pytest.mark.oob`; `guard_pytest` fails any that reads one untagged, so running the suite after declaring the scope
finds them. A test that reads `oob/` through a subprocess isn't seen by `guard_pytest`, so the candidates
(`test_oob.py`, `test_org_profile.py`, `test_plan_needed.py`, `test_dependabot_issues_workflow.py`, by `grep oob/`) are
read by hand too. `scripts/oob.py` is Python, which has no scope, so a change to it still runs the full check.

### D3. The limit and the tofu gates stay as they are

With D1 the full check is about 190 s against 600 s, so the limit has room without changing the guard. Raising it, or
saying "stopped for time" in its message, would change a delivered file and need a delivery plan, for no gain once the
check fits. Skipping `tofu init` and `tofu validate` for scopes that don't touch `tofu/` would change the
development-workflow requirement every repository shares, to save under 4 s once a worktree has run `tofu init`.

## Risks / Trade-offs

- **A test that depends on another test's side effects, or on running alone, could fail under workers.** The full suite
  passed under `-n 4` on the base commit; the apply runs it again. If one flakes later, `--dist loadfile` or an xdist
  group for that file is the fix, not going back to serial.
- **Each commit uses up to 4 cores for about 3 minutes, instead of 1 core for about 9.** On a loaded machine that's more
  load for less time; the total CPU time is the same (about 280 s).
- **The 600 s limit stays fixed.** If the suite grows back towards it, the before/after numbers here are the baseline
  to compare with.
