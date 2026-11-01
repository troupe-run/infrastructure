# Proposal

## Why

Each review run joins one concurrency group per pull request, so a newer push or reply cancels a review still running.
That's safe while a later run reviews the head, but if the **last** run is cancelled or fails, the head isn't reviewed
by anyone. Nothing notices: `claude review` isn't a required check, and "nothing open" after a review that never ran
looks the same as a clean review (#242, raised after #240 saw a review cancelled for concurrency). The owner decided
on 2026-10-31 to fix it with a required check.

## What Changes

- A new job at the end of `.github/workflows/claude-review.yml`, **`claude review completed`**, reports on the pull
  request's head:
  - passes when that run's review and its resolving job both succeeded;
  - fails when the review (or the gate in front of it, or the resolving job) was cancelled or failed. Its message
    names the run to re-run (`gh run rerun <id>`);
  - is pending while the review runs, because it waits for the review's jobs;
  - passes when the pull request isn't reviewed by design (a bot's pull request, such as Dependabot's or
    release-please's, or a fork's);
  - runs only for pull request events. GitHub counts only the newest pull request event's run for a pull request,
    so a comment's run can neither hide a cancelled review nor pass one (probed on a throwaway repository). A reply
    whose review cancels a push's running review leaves the check failed until the push's run is re-run;
  - is skipped on `merge_group`, which counts as passed, so the merge queue isn't held up. `claude-review.yml` gains
    `merge_group:` for that alone (merge-queue design D5's pattern).
- `tofu/required-checks.json` requires `claude review completed` in troupe, infrastructure and website. The workflow
  reaches troupe and website by the usual guard delivery, in the same approved apply.
- **BREAKING (process):** a failed or cancelled last review now blocks the merge until it's re-run. That includes a
  review that fails because its Claude credential expired: every member's pull request in the three repositories
  waits until the token is renewed and the run re-run, or the owner bypasses the rules.
- `docs/development-workflow.md` says, next to "the review of the last push", that the check holds a pull request
  until the review of its head has completed, and how to re-run it.
- A probe on a throwaway repository settled, before the job was written, which runs GitHub counts for a pull request
  (design.md, "Probe results").

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pr-review`: the review stays advisory in what it finds, but a new check reports whether the review of the head
  completed; "The review is advisory" and the expired-token scenario change, and new requirements say what the check
  reports in each case.
- `rulesets`: a new requirement that troupe, infrastructure and website each require `claude review completed`.
  "Each repository requires its own checks" stays as it is: adding the check to it pushed it past 500 characters.
- `development-workflow`: a new requirement that `docs/development-workflow.md` says, next to "the review of the last
  push", that the check holds a pull request whose last review didn't complete, and how to re-run it. "A pull request
  opens as a draft and is marked ready once its review is clean" stays as it is.

## Impact

- `.github/workflows/claude-review.yml` (a new trigger and job; delivered to troupe and website).
- `scripts/tests/test_claude_review_workflow.py` (pins the job and tests its script).
- `tofu/required-checks.json`, and the tests that hold it equal to the workflows.
- `docs/development-workflow.md`, `CLAUDE.md` if its step 5 needs it.
- Open pull requests in the three repositories get the check on their next push; until then they can't merge. One
  push or a fresh review run gives them the check.
- A throwaway `troupe-run/infra-probe-*` repository for the probe, deleted afterwards.
