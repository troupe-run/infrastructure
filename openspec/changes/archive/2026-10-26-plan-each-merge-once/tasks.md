# Tasks

## 0. The issue and the owner's decision

- [x] 0.1 Set #167's card to In Progress. Done: `gh issue view 167 -R troupe-run/infrastructure --json projectItems`
      shows In Progress (2026-10-26)
- [x] 0.2 Owner: accept the one case that still plans nothing (design D1, Risks: state committed after a later merge,
      from an apply whose plan predates the earlier merge), and the deviation from #167's "plans nothing" (proposal).
      Record the answer here before the pull request. (It was "before 2.1"; the answer changes only that one case
      in the script, not the workflow's wiring, so 2.x went ahead.) Done (owner, 2026-10-26): both accepted

## 1. The decision script (design D1, D2)

- [x] 1.1 Write `scripts/tests/test_plan_target.py` first, with real temporary repositories (conftest's `git`
      helper): state commits as the App's address changing only `tofu/terraform.tfstate`, merges as the tester. One
      test per case, each named for its answer: a scheduled or manual run plans `main`'s head; a state commit as C
      plans nothing; C not on `main` fails naming C; C with the current state plans C, with and without later merges;
      only state commits after C plans `main`'s head (#167's sequence); state commits then a later merge plans the last
      of those state commits; a state commit after a later merge plans nothing and names that merge; a break-glass
      merge that changes the state under another author doesn't count as a state commit; an unknown event, or a
      commit that isn't a full sha, is an error naming the input. Verify they fail (no script yet) with
      `uv run pytest scripts/tests/test_plan_target.py`. Done: collection failed on the missing module; a state-only
      commit by someone else was added as a case too
- [x] 1.2 Write `scripts/plan_target.py`: standard library and `git` only, `--event`, `--commit`, `--state-author`,
      `--main` (default `origin/main`); prints `sha=` and `plan=` for `$GITHUB_OUTPUT`, and one summary line to the
      file `--summary` names. Verify 1.1's tests pass, and `uv run scripts/check.py` is clean (ruff, mypy --strict).
      Done: 26 passed, all gates passed. With the walk over state commits removed, 5 of them fail

## 2. The workflow (design D3)

- [x] 2.1 In `tofu.yml`'s `plan` job, replace "The commit to plan" and "Skip the App's own state commit" with: checkout
      of `main` (`fetch-depth: 0`), a step running `plan_target.py` (id `target`, passing `STATE_AUTHOR` and the
      event's commit), and `git checkout --detach` of its `sha` when `plan` is true. Point the job's `sha` output, the
      guard wait, the plan heading and every later step's `if` at the `target` step. Update the header comment and the
      comment on the guard wait. Verify with `uv run scripts/check.py`. Done: all gates passed. The script runs with
      the runner's `python3`, as `plan_needed.py` does, since uv isn't set up yet
- [x] 2.2 Add a workflow test (in `test_plan_display_workflow.py`'s style, or a new `test_plan_target_workflow.py`):
      the script runs before the checkout of its commit; every later step in `plan` is gated on its `plan` output; the
      `sha` output, the guard wait and the apply's checkout read its `sha`; no step reads
      `github.event.workflow_run.head_sha` but the script's. Parametrised mutations break each link and expect a named
      problem. Verify the test passes, and that each mutation fails it. Done: `test_plan_target_workflow.py`, 1 pass on
      the real workflow and 13 mutations each caught
- [x] 2.3 Move `test_required_checks.py`'s state-commit check from the removed step to `plan_target.py`'s state-path
      constant, still compared with CI's `paths-ignore`. Verify it passes, and fails when the constant changes. Done:
      22 passed, including a changed constant and a plan job without the script, each named

## 3. Docs

- [x] 3.1 README "Running a plan": which run applies a merge (its own run after CI, planning with `main`'s current
      state; a scheduled run that got there first leaves it nothing to approve), and that a run's summary names the
      commit it planned. Verify `uv run scripts/check.py --scope docs` passes, and the paragraph matches D1. Done:
      the docs check passed

## 4. Evidence

- [x] 4.1 Full `uv run scripts/check.py` passes. Open the pull request with `Closes #167`. Done: all gates passed
      rebased on `472ee1e`; PR #176. Its plan's evidence moved to the follow-up below: the plan run waits for the
      owner's approval, which is asked once, after this archive's push

## Workflow follow-up

- After this archive is pushed, the owner approves PR #176's `plan (pull request)` run. Its comment should show "No
  changes" (no `tofu/` change).
- `/opsx:archive` on the branch before merging; the owner merges by rebase.
- After the merge, the merge's own `tofu` run's summary should say it planned its own commit (its state is current).
  Recorded on #167 with the after-merge comment. (This was task 4.2; it can only be seen after the archive.)
- After the merge: comment on #167 with the PR and the archived change, check it's closed, and set its card to Done.
- If the owner wants it: an issue for whether a scheduled or manual run waits for green CI before it can apply
  (design, Open Questions), on the board.
