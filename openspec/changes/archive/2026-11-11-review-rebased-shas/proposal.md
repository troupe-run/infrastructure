## Why

Pull requests merge by rebase, so every commit lands on `main` with a new SHA (troupe-run/troupe#326's `df0c5621`
landed as `4f930093`). A commit SHA cited in a change, such as a task's "CI run N on `<sha>`", never names a commit on
`main`, however carefully it's kept up to date. Claude's review files "a stale reference" as a nit, so after each
rebase it flags the SHAs the rebase removed. An open nit blocks the merge until a push fixes it (another review, and
after a rebase another CI wait) or it's answered and resolved. On troupe#315 this came round several times, and on
troupe#287 it was raised as a must-fix. The owner, 2026-11-09: re-citing after a rebase isn't worth it, since the
reference won't survive the merge anyway (#294).

## What Changes

- The review prompt in `.github/workflows/claude-review.yml` says that a commit SHA which names no commit on the pull
  request's branch is not a finding, at any tier, and says why: merging by rebase rewrites every SHA, so no cited SHA
  survives the merge. It doesn't ask for one to be re-cited.
- The same prompt says a ticked task is still judged as it is now, by its code and verification in the pull request.
  A CI run id the task cites is still evidence; a SHA beside it neither adds nor takes away from that.
- Other stale references (a moved file, a removed function, an out-of-date doc) stay nits, as now.
- A test pins the new sentences in the prompt, and the "Claude's review" section of `docs/development-workflow.md`
  says the same, so an agent knows not to re-cite either.
- The workflow is delivered to troupe and website with the guard's files, as every change to it is.

Out of scope: the coverage gate failing clean reviews (#281); giving the review a way to look a CI run up
(`gh run view` isn't one of its tools, and isn't needed for this); other kinds of stale reference.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pr-review`: a new requirement that a commit SHA a rebase removed isn't a review finding, while a ticked task's
  verification is still checked.

## Impact

- `.github/workflows/claude-review.yml`: the prompt only. No step, permission, tool or trigger changes.
- `scripts/tests/test_claude_review_workflow.py`: a test that the prompt says it.
- `docs/development-workflow.md`: "Claude's review".
- Delivery: after the merge, the plan updates `claude-review.yml` in troupe and website. The owner approves the apply.
  Before then, troupe's `uv run scripts/check.py` and website's workflow test run with the new file in place.
