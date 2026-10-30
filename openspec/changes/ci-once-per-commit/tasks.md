# Tasks

## 1. Check what the change relies on

- [ ] 1.1 Check the guard allows both commands as it stands: run `uv run scripts/guard.py` on a `gh pr create
  --draft --title … --body-file <file with Closes #232>` and a `gh pr ready 1` tool call (as
  `test_guard_gh.py` does) and record the decisions here. If either is refused, add the rule change and a test that
  fails without it to group 4 before going on.
- [ ] 1.2 Confirm a CI run whose `check` and legs are skipped concludes `success` (design Context): find a recent
  docs-only pull request's CI run with `gh run list --workflow ci.yml --event pull_request --json conclusion,databaseId`
  and `gh run view <id> --json jobs`, and record the run here.

## 2. The merge queue's lookup (design D1, D3, D4)

- [ ] 2.1 Write `scripts/queue_passed.py`: given `--repository` and `--sha`, read CI's `merge_group` runs on that
  commit through `gh run list`, print `scope=none`/`check-args=`/`guard=false` when one completed with success,
  and otherwise `scope=full`/`check-args=`/`guard=true`. Poll a run still waiting every 10 s for up to 2 minutes.
  Answer "full" with a `::warning::` naming why on a failed read, unparseable output or an unknown status, and always
  exit 0. Standard library, with an injected `gh` callable, as `main_ci.py` has.
- [ ] 2.2 Add `scripts/tests/test_queue_passed.py`, each test named for what it checks: a successful queue run skips,
  no queue run runs all, a failed or cancelled one runs all, a run that completes during the wait is waited for, one
  still running at the limit runs all, a failed read and unparseable output run all with a warning and exit 0, and
  only `--event merge_group` runs of `ci.yml` are asked for. Verify `uv run pytest scripts/tests/test_queue_passed.py`
  passes, and that mypy --strict and ruff are clean.
- [ ] 2.3 Run the script against GitHub for real: `python3 scripts/queue_passed.py --repository
  troupe-run/infrastructure --sha $(git rev-parse 4a64b25)` answers `scope=none`, and the same for an App state
  commit (no CI run) answers `scope=full`. Record both outputs here.

## 3. ci.yml and tofu.yml (design D2)

- [ ] 3.1 In `ci.yml`: add `ready_for_review` to `pull_request`'s types (written out with opened, synchronize and
  reopened). Run `changes` on `github.event_name != 'merge_group'` with `actions: read`. Give it three exclusive
  steps: a draft (`scope=none`, `guard=false`, and a notice saying the legs run when it's marked ready), a push
  (`queue_passed.py` with `github.sha`), and a ready pull request (the changed paths, unchanged). Keep `check`'s, the
  legs' and `guard tests`' conditions as they are. Rewrite the header comment's D7 sentence and run list to say a
  push to `main` skips a commit the queue passed and a draft runs nothing until ready.
- [ ] 3.2 Update `scripts/tests/test_ci_workflow.py`: pin `changes`' new condition and permissions, the
  `pull_request` types, the draft step's answers and the push step's script, and add a mutation case for each (drop
  `ready_for_review`, `changes` only on pull requests, the draft step removed) that the problems list names. Verify
  `uv run pytest scripts/tests/test_ci_workflow.py` passes.
- [ ] 3.3 In `tofu.yml`: add `ready_for_review` to `pull_request`'s types. Add a step to `changes` that answers
  `plan=false` on a draft, with a notice, and skip the paths step for a draft. Leave `pr-plan`'s condition
  unchanged. Update the trigger table in the header comment. Add tests (in the existing tofu workflow test file that
  pins `changes`, or a new one) for the types and the draft answer, and a mutation case for each. Verify they pass.

## 4. Marking ready doesn't start a review (design D5)

- [ ] 4.1 Drop `ready_for_review` from `claude-review.yml`'s `pull_request` types, with a comment citing this
  change's design D5, and update `EVENTS` and its mutation case in `scripts/tests/test_claude_review_workflow.py`.
  Verify the test passes, and that `guard_tests_needed.py` still lists the file, so every leg runs on this pull
  request.

## 5. The draft-then-ready step in the docs (design D6)

- [ ] 5.1 In `docs/development-workflow.md`, "Claude's review": add the step (open as a draft with `gh pr create
  --draft`, act on the findings, `gh pr ready <n>` once the review of the last push has nothing left to fix), why CI
  and the plan wait for it, and that marking ready starts no review. Verify the docs checks in
  `uv run scripts/check.py` pass.
- [ ] 5.2 Update `CLAUDE.md`'s "How work happens here", steps 4 and 5, to match, in the same words as 5.1.
- [ ] 5.3 Update `org-profile/CONTRIBUTING.md`'s "How work flows", steps 3 and 4, to match. Verify the org-profile
  tests pass, and a local plan shows only `CONTRIBUTING.md`'s content changing in `troupe-run/.github`.

## 6. Whole-change checks

- [ ] 6.1 Run `uv run scripts/check.py` (full) and `openspec validate ci-once-per-commit --strict`; both pass.
- [ ] 6.2 Open the pull request as a draft (`gh pr create --draft`, `Closes #232`). Verify on its runs that CI's
  `check` and legs are skipped with `guard tests` green, and `plan (pull request)` is skipped without asking for
  approval. Record the run links here.
- [ ] 6.3 Act on Claude's review of the last push by tier. Once nothing is left to fix, `gh pr ready <n>`. Verify the
  legs run, `plan (pull request)` asks for approval, and no review run starts. Ask the owner to approve the plan, and
  check it shows `claude-review.yml` delivered to troupe and website and `CONTRIBUTING.md` to `.github`.

## Workflow follow-up

- Archive the change on the branch (`/opsx:archive`), rebase onto main's state commit if needed, and let the owner
  merge through the queue.
- After the merge, verify CI's push run on `main` skips `check` and the legs, ends in success, and `plan (main)`
  starts (design Migration Plan, step 3). Record it in the issue comment.
- Comment on #232 with the PR and the archived change, close it, and check its card on the roadmap board is Done.
