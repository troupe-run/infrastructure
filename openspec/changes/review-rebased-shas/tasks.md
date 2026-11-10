# Tasks

## 1. The prompt lets a rebased SHA pass (design D1 to D3)

- [x] 1.1 Add a test in `scripts/tests/test_claude_review_workflow.py`, named for what it checks (the prompt says a
  commit SHA that names no commit on the branch isn't a finding, why, and that a cited CI run id is still evidence),
  that flattens the prompt's whitespace and asserts those phrases. Verify it fails on the current workflow:
  `uv run pytest scripts/tests/test_claude_review_workflow.py -k sha` fails, naming the missing phrase
- [x] 1.2 In `.github/workflows/claude-review.yml`, add D2's sentences to check 2, after the rule that a task is
  ticked only if its code and verification are in the pull request: a commit SHA cited in the pull request that names
  no commit on its branch isn't a finding, at any tier, and isn't to be re-cited, because pull requests merge by
  rebase, which rewrites every SHA; a ticked task is still judged by its code and verification, and a CI run id it
  cites is still evidence. Leave the nit tier's "a stale reference" as it is. Change nothing outside the prompt.
  Verify that `uv run pytest scripts/tests/test_claude_review_workflow.py` passes, including 1.1's test, and that
  `git diff --stat` shows only the prompt's lines changed in the workflow

## 2. The docs say there's no need to re-cite (design D4)

- [x] 2.1 In `docs/development-workflow.md`, "Claude's review", add a sentence after the tier table: the review
  doesn't flag a cited commit SHA that a rebase removed, since merging by rebase rewrites every SHA, so a SHA needn't
  be re-cited after a rebase; a ticked task's code and verification are still checked. Verify that
  `uv run pytest scripts/tests/test_guard_docs.py` passes and `grep -n "re-cited" docs/development-workflow.md` shows
  the sentence

## 3. The delivered copies still pass their repositories' checks

- [ ] 3.1 In scratch clones of troupe-run/troupe and troupe-run/website (in the scratchpad, deleted afterwards), put
  this branch's `claude-review.yml` in place and run troupe's `uv run scripts/check.py` and website's
  `npx vitest run tests/unit/workflow-node-version.test.ts`. Verify both pass, and quote their last lines in the pull
  request

## 4. Whole-change verification

- [ ] 4.1 Run `uv run scripts/check.py` and `openspec validate review-rebased-shas --strict`. Both pass. Show the
  output
- [ ] 4.2 After rebasing this branch onto `main` at least once while the pull request is open (as happens anyway
  before the merge), read the review run for the head (it runs the new prompt): it raises no finding about the SHAs
  this change's tasks cite from before the rebase. Quote the run's ID and the summary's line on it in the pull
  request

## Workflow follow-up

- After the merge, the plan on `main` should show only the delivery of `claude-review.yml` to troupe and website. The
  owner approves the apply.
- Archive on the branch before merging. After the merge, comment on #294 with the PR and the archived change, check
  it's closed, and check that its card says Done.
