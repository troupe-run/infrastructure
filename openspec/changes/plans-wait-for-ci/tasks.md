# Tasks

## 1. The gate script (spec ci-apply, "A scheduled or manual plan of main waits for green CI", "A red main fails a scheduled or manual plan, saying how to recover"; design D1-D4)

- [x] 1.1 Move `History` (and its fixture) from `scripts/tests/test_plan_target.py` to `scripts/tests/conftest.py`,
  so both scripts' tests build `main`'s history the same way, with a `state_only()` helper for a person's
  state-only commit (a break-glass state merge). Verify `uv run pytest scripts/tests/test_plan_target.py` passes
  unchanged.
- [x] 1.2 Write `scripts/tests/test_main_ci.py` first, each test named for what its body checks, with `gh` and the
  clock passed in (no network, no real sleep): CI passed on the head merge plans; the App's state commit at the head
  is looked past to the merge before it; a person's state-only commit with no CI run is looked past; a state-only
  last commit that has a CI run is the one checked; a merge with no run yet waits, and is found once a run appears;
  queued then in progress then success passes; in progress then failure fails; each non-success conclusion
  (`failure`, `cancelled`, `timed_out`, `startup_failure`, `action_required`, `neutral`, `skipped`, `stale`) fails;
  an unknown status fails naming it; a failed `gh` read fails with its error; the limit fails with "didn't finish"
  and the commit; the failure summary names the commit's short sha and subject, links the run, and lists the three
  ways to recover; a pass writes one line to the summary. Verify they fail before 1.3 (no module).
- [x] 1.3 Write `scripts/main_ci.py` (standard library and `gh`; `STATE_PATH` imported from `plan_target`; limit 25
  minutes, poll 15 s, as named constants) to D2-D4. Verify `uv run pytest scripts/tests/test_main_ci.py` passes,
  and `uv run scripts/check.py` is clean (mypy --strict, ruff).
- [x] 1.4 Run it read-only against this repository's real `main` (`python3 scripts/main_ci.py --main origin/main
  --summary <scratch file>` after a fetch), and verify it names the right commit and CI run (compare with
  `gh run list --workflow ci.yml --branch main --event push -L 3`) and passes or waits as that run's state says.
  Record the output in the pull request.

## 2. Wiring it into `tofu.yml` (design D1, D3, D5, D6)

- [x] 2.1 Write `scripts/tests/test_main_ci_workflow.py` first, pinning: the `plan` job runs `scripts/main_ci.py` in
  exactly one step, after `The commit to plan` and before the guard wait; its `if:` is
  `github.event_name != 'workflow_run' && steps.target.outputs.plan == 'true'`; it passes `--main origin/main`,
  `--summary "$GITHUB_STEP_SUMMARY"` and `GH_TOKEN`; the job's `timeout-minutes` exceeds the script's limit plus the
  guard wait's 10 minutes; `ci.yml`'s `push` `paths-ignore` is exactly `[plan_target.STATE_PATH]`;
  `workflow_dispatch` has no inputs; the `oob` job has no `needs` and doesn't run the gate. Verify each test fails on
  the current `tofu.yml` where it should (the step, the timeout).
- [x] 2.2 Add the step to `tofu.yml`'s `plan` job, raise its timeout to 45 minutes, and update the comments (the
  header table, and the guard wait's "After a merge, CI has passed" comment to cover scheduled and manual runs).
  Verify `test_main_ci_workflow.py`, `test_plan_target_workflow.py` and `test_oob_job.py` pass, and
  `uv run scripts/check.py` is clean.

## 3. Docs (proposal, What Changes)

- [x] 3.1 In README.md's "Running a plan", say that a scheduled or manual plan of `main` waits for CI on `main`, that
  a red `main` fails those runs with a summary saying why, and the three ways to recover; and that the drift job
  still runs. Verify `uv run scripts/check.py` is clean (its docs checks included), and grep the README for any
  statement this contradicts ("whatever commit", "daily plan").

## 4. Integration

- [ ] 4.1 Run `openspec validate plans-wait-for-ci --strict` and the full `uv run scripts/check.py`. Verify both are
  clean, and that the pull request's `plan (pull request)` shows no OpenTofu changes.

## Workflow follow-up

- After the merge, a manual run on `main` (`gh workflow run tofu.yml --ref main`, by the owner if the guard refuses
  it) shows the gate in use: its summary names the commit CI ran on and says CI passed. Link it on #178.
- Archive on the branch before merging, comment on #178 with the PR and the archived change, close it, and check its
  card says Done.
