# Proposal

## Why

When 0.1.0 closed (#244, #245), the plan said every repository had no open issues with no milestone, while there were
14 (#247). The pull request's plan job reads the list with its own `GITHUB_TOKEN`, which holds `pull-requests: write`
and no issues permission. A probe showed GitHub then answers the issues list with only the pull requests (troupe: 10
of 67 open items), the script drops those, and every repository reads as "none". That is the silently short list the
milestones spec forbids, and it skipped the owner's review of each unmilestoned issue before the release closed. The
plan of `main` reads correctly today, but only because its token holds neither permission and the repositories are
public.

## What Changes

- Both steps (`pr-plan` and `plan`) read with a token minted from the troupe-run-infrastructure App, whose key the
  plan jobs already hold. The token is limited to the four milestone repositories, `issues: read` and
  `pull-requests: read` (with the `metadata: read` every App token has). The jobs' `GITHUB_TOKEN` permissions don't
  change.
- The App gains `pull_requests: read` (owner, 2026-11-02): granted by the owner in its settings, and declared in
  `oob/app-installations.json` so the drift check agrees.
- `scripts/milestone_review.py` refuses an answer it can't trust: it checks what it read against the repository's
  count of open issues and pull requests, and fails, naming the repository, when the token saw fewer. So a later
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
- `oob/app-installations.json`: troupe-run-infrastructure's `pull_requests: read`. No OpenTofu change, no secret.
- The workaround in use until now (running the script locally on a local plan before closing a milestone) is no
  longer needed once this is on `main`.
