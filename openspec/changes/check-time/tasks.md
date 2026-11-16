# Tasks

Load rule for every timed or full run below: check `uptime` first, start only when the 1-minute load is under 40, and
run one at a time.

## 1. Parallel tests in the check (design D1)

- [ ] 1.1 Write the tests first in `scripts/tests/test_check.py`: the full check's pytest command carries
      `-n <min(TEST_WORKERS, cpu_count)>`; with fewer CPUs than `TEST_WORKERS` (cpu count patched to 2, and to `None`)
      it carries `-n 2` and `-n 1`; a scoped command carries both `-n` and `-m`. Verify they fail on the base code
- [ ] 1.2 Add `TEST_WORKERS = 4` and the `-n` argument to `gates()` in `scripts/check.py`, and update its docstring.
      Verify 1.1's tests pass, and `uv run pytest scripts/tests/test_check.py` passes
- [ ] 1.3 Verify a scoped run that selects nothing still passes under xdist: a test runs pytest with `-n 2 -m <a marker
      no test has>` over a tiny pytester project and checks it exits 5, which `run_gates` treats as nothing to test

## 2. An `oob` scope (design D2)

- [ ] 2.1 Declare `[scopes.oob] paths = ["oob/**"]` in `scripts/check-paths.toml`, with a comment naming what reads it.
      Run the full suite and tag `oob` every test `guard_pytest` reports as reading `oob/` untagged. Read the four
      candidate files (`test_oob.py`, `test_org_profile.py`, `test_plan_needed.py`,
      `test_dependabot_issues_workflow.py`) for reads made through a subprocess, and tag those by hand. Verify the full
      suite passes
- [ ] 2.2 Verify `echo oob/projects.json | uv run scripts/guard.py check-scope` answers `oob`, and
      `uv run scripts/check.py --scope oob` passes and runs only the `oob`-tagged tests

## 3. Before and after

- [ ] 3.1 Time `uv run scripts/check.py` on this branch (full check), and record each gate's time and the load averages
      beside design's "before" table. Verify the full check takes under half the 600 s limit
- [ ] 3.2 Make a commit touching only `docs/` and one touching only `oob/` (each with nothing else staged) and record
      the guard's announcement and its "passed in Ns" line. Verify each runs the scoped check and passes well under the
      limit (under 120 s)
- [ ] 3.3 Run `uv run scripts/check.py` (the full check) once more, and `openspec validate check-time --strict`. Verify
      both pass

## Workflow follow-up

- Open the draft pull request with `Closes #310`, its body giving the before and after times.
- Act on Claude's review of the last push; mark ready once it's clean; CI runs the full check.
- Archive the change on the branch, then the owner merges by rebase through the merge queue.
- After the merge: check #310 is closed and its card says Done; comment on #310 with the PR and the archived change.
