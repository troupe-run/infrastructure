# Tasks

## 1. Check what the change relies on

- [x] 1.1 Check the guard allows both commands as it stands: run `uv run scripts/guard.py` on a `gh pr create
  --draft --title … --body-file <file with Closes #232>` and a `gh pr ready 1` tool call (as
  `test_guard_gh.py` does) and record the decisions here. If either is refused, add the rule change and a test that
  fails without it to group 4 before going on. Done 2026-10-30, through `guard.py claude-pre-tool-use` on this
  branch: `gh pr create --draft … --body-file <Closes #232>` is allowed (exit 0, no decision, so Claude Code's own
  check applies), and `gh pr ready 1` is allowed and granted. The same create without a closing reference is denied
  by `pr-closes-issue`, so the harness reads the guard's decisions. No rule changes.
- [x] 1.2 Confirm a CI run whose `check` and legs are skipped concludes `success` (design Context): find a recent
  docs-only pull request's CI run with `gh run list --workflow ci.yml --event pull_request --json conclusion,databaseId`
  and `gh run view <id> --json jobs`, and record the run here. Done: none of the last 60 skipped `check`, but
  run 41052435449 (legs skipped, `changes`, `check` and `guard tests` succeeded) concluded `success`. A run with
  every job skipped concludes `skipped` (tofu's merge-group runs), so the push run keeps `changes` and `guard tests`
  running; design Context says so.

## 2. The merge queue's lookup (design D1, D3, D4)

- [x] 2.1 Write `scripts/queue_passed.py`: given `--repository` and `--sha`, read CI's `merge_group` runs on that
  commit through `gh run list`, print `scope=none`/`check-args=`/`guard=false` when one completed with success,
  and otherwise `scope=full`/`check-args=`/`guard=true`. Poll a run still waiting every 10 s for up to 2 minutes.
  Answer "full" with a `::warning::` naming why on a failed read, unparseable output or an unknown status, and always
  exit 0. Standard library, with an injected `gh` callable, as `main_ci.py` has.
- [x] 2.2 Add `scripts/tests/test_queue_passed.py`, each test named for what it checks: a successful queue run skips,
  no queue run runs all, a failed or cancelled one runs all, a run that completes during the wait is waited for, one
  still running at the limit runs all, a failed read and unparseable output run all with a warning and exit 0, and
  only `--event merge_group` runs of `ci.yml` are asked for. Verify `uv run pytest scripts/tests/test_queue_passed.py`
  passes, and that mypy --strict and ruff are clean.
- [x] 2.3 Run the script against GitHub for real: `python3 scripts/queue_passed.py --repository
  troupe-run/infrastructure --sha $(git rev-parse 4a64b25)` answers `scope=none`, and the same for an App state
  commit (no CI run) answers `scope=full`. Record both outputs here. Done 2026-10-30: 4a64b25 answered
  `scope=none`/`guard=false` ("the merge queue passed 4a64b25…"); the state commit 2adb29e answered
  `scope=full`/`guard=true` ("no merge-queue run of CI tested 2adb29e…"); a repository that doesn't exist answered
  `scope=full` with a `::warning::` naming the 404. Each exited 0.

## 3. ci.yml and tofu.yml (design D2)

- [x] 3.1 In `ci.yml`: add `ready_for_review` to `pull_request`'s types (written out with opened, synchronize and
  reopened). Run `changes` on `github.event_name != 'merge_group'` with `actions: read`. Give it three exclusive
  steps: a draft (`scope=none`, `guard=false`, and a notice saying the legs run when it's marked ready), a push
  (`queue_passed.py` with `github.sha`), and a ready pull request (the changed paths, unchanged). Keep `check`'s, the
  legs' and `guard tests`' conditions as they are. Rewrite the header comment's D7 sentence and run list to say a
  push to `main` skips a commit the queue passed and a draft runs nothing until ready.
- [x] 3.2 Update `scripts/tests/test_ci_workflow.py`: pin `changes`' new condition and permissions, the
  `pull_request` types, the draft step's answers and the push step's script, and add a mutation case for each (drop
  `ready_for_review`, `changes` only on pull requests, the draft step removed) that the problems list names. Verify
  `uv run pytest scripts/tests/test_ci_workflow.py` passes.
- [x] 3.3 In `tofu.yml`: add `ready_for_review` to `pull_request`'s types. Add a step to `changes` that answers
  `plan=false` on a draft, with a notice, and skip the paths step for a draft. Leave `pr-plan`'s condition
  unchanged. Update the trigger table in the header comment. Add tests (in the existing tofu workflow test file that
  pins `changes`, or a new one) for the types and the draft answer, and a mutation case for each. Verify they pass.
  Done in a new `scripts/tests/test_tofu_drafts.py`. `test_required_checks.py`'s `runs_on_pull_requests` read
  `changes`' new `github.event_name != 'merge_group'` as confining it to other events, which dropped `check` and
  `guard tests` from the pull request checks. It now treats a condition that only excludes another event as running
  on pull requests.

## 4. Marking ready doesn't start a review (design D5)

- [x] 4.1 Drop `ready_for_review` from `claude-review.yml`'s `pull_request` types, with a comment citing this
  change's design D5, and update `EVENTS` and its mutation case in `scripts/tests/test_claude_review_workflow.py`.
  Verify the test passes, and that `guard_tests_needed.py` still lists the file, so every leg runs on this pull
  request.
  Done 2026-10-30: the test passes, and `.github/workflows/claude-review.yml` is in `DEPENDS_ON`. As the file's
  header asks before a delivery (#155), fresh clones of troupe and website with it in place pass troupe's
  `uv run scripts/check.py` (2991 passed) and website's `npx vitest run tests/unit/workflow-node-version.test.ts`
  (8 passed).

## 5. The draft-then-ready step in the docs (design D6)

- [x] 5.1 In `docs/development-workflow.md`, "Claude's review": add the step (open as a draft with `gh pr create
  --draft`, act on the findings, `gh pr ready <n>` once the review of the last push has nothing left to fix), why CI
  and the plan wait for it, and that marking ready starts no review. Verify the docs checks in
  `uv run scripts/check.py` pass.
- [x] 5.2 Update `CLAUDE.md`'s "How work happens here", steps 4 and 5, to match, in the same words as 5.1.
- [x] 5.3 Update `org-profile/CONTRIBUTING.md`'s "How work flows", steps 3 and 4, to match. Verify the org-profile
  tests pass, and a local plan shows only `CONTRIBUTING.md`'s content changing in `troupe-run/.github`. The
  org-profile tests pass. The plan is read from CI's plan on the pull request (6.3) rather than a local one, which
  would need the 1Password secrets and shows the same thing.

## 6. Whole-change checks

- [x] 6.1 Run `uv run scripts/check.py` (full) and `openspec validate ci-once-per-commit --strict`; both pass.
- [x] 6.2 Open the pull request as a draft (`gh pr create --draft`, `Closes #232`). Verify on its runs that CI's
  `check` and legs are skipped with `guard tests` green, and `plan (pull request)` is skipped without asking for
  approval. Record the run links here. Done: #234 opened as a draft. CI run 41063386548 concluded success with
  `check` and the legs skipped and `guard tests` passing; tofu run 41063386319 skipped `plan (pull request)`, asking
  no approval. 6.1: the full check and `openspec validate --all --strict` (23) passed.
- [ ] 6.3 Act on Claude's review of the last push by tier. Once nothing is left to fix, `gh pr ready <n>`. Verify the
  legs run, `plan (pull request)` asks for approval, and no review run starts. Ask the owner to approve the plan, and
  check it shows `claude-review.yml` delivered to troupe and website and `CONTRIBUTING.md` to `.github`.

## Workflow follow-up

- Archive the change on the branch (`/opsx:archive`), rebase onto main's state commit if needed, and let the owner
  merge through the queue.
- After the merge, verify CI's push run on `main` skips `check` and the legs, ends in success, and `plan (main)`
  starts (design Migration Plan, step 3). Record it in the issue comment.
- Comment on #232 with the PR and the archived change, close it, and check its card on the roadmap board is Done.
