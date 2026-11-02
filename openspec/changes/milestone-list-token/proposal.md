# Proposal

## Why

When 0.1.0 closed (#244, #245), the plan said every repository had no open issues with no milestone, while there were
14 (#247). Both "Issues with no milestone" steps in `.github/workflows/tofu.yml` read with the job's `GITHUB_TOKEN`,
which has no issues permission. GitHub then answers the issues list with only the pull requests, the script drops
those, and every repository reads as "none". That is the silently short list the milestones spec forbids, and it
skipped the owner's review of each unmilestoned issue before the release closed. A `GITHUB_TOKEN` can't be given
issues read on troupe or website at all, so the job's permissions can't fix it.

## What Changes

- Both steps (`pr-plan` and `plan`) read with a token minted from the troupe-run-infrastructure App, whose key the
  plan jobs already hold. The token is limited to the four milestone repositories and `issues: read` (with the
  `metadata: read` every App token has). The jobs' `GITHUB_TOKEN` permissions don't change.
- `scripts/milestone_review.py` refuses an answer it can't trust: it checks what it read against the repository's
  count, and fails, naming the repository, when the token saw fewer. Which count is settled by a test first (design
  D2): an issues-only token may not list pull requests, and `open_issues_count` includes them. So a later
  token change can't empty the list again without the step going red.
- The workflow tests pin the new token: the App, the repositories and the permissions, and that the step uses it.
- The comments in `tofu.yml` and the script's docstring say which token reads and why.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `milestones`: two new requirements: the list is read with an App token that can see issues, not the job's own
  token; and a read that comes up short of GitHub's own count fails the step.

## Impact

- `.github/workflows/tofu.yml`: a token step before each "Issues with no milestone" step, and that step's
  `GH_TOKEN`.
- `scripts/milestone_review.py` and `scripts/tests/test_milestone_review.py`: the count check.
- `scripts/tests/test_milestone_review_workflow.py`: pins the minted token in place of the job's own.
- No OpenTofu change, no new App permission (troupe-run-infrastructure already has `issues: write` on all four
  repositories, `oob/app-installations.json`), no secret.
- The workaround in use until now (running the script locally on a local plan before closing a milestone) is no
  longer needed once this is on `main`.
