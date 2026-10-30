# Proposal

## Why

Milestones have been read two ways at once: the release an issue is needed for, and the release that was in progress
when it was done. So 0.1.0 kept filling with work it doesn't need, and a milestone stopped answering "what's left
before this release". #226 (owner, 2026-10-30) settled it: a milestone holds only what its release needs, everything
else has no milestone, and the issues with no milestone are reviewed whenever a release closes. This change writes that
rule down and builds it in (#229). Re-sorting the existing issues is #230, after this.

## What Changes

- **The org's guide** (`org-profile/CONTRIBUTING.md`): the "Milestones" section says an issue goes in a milestone only
  if that release would wait for it, so improvements, process and org upkeep, flaky tests outside an Epic a release
  needs, and version bumps have none, open or closed. A follow-up takes its origin's milestone only when the origin
  needs it. Decisions are unchanged. When a milestone is closed, every open issue with no milestone is moved into a
  milestone, `parked` with a reason, or closed as not planned. The "Completed work always has a milestone" rule goes.
  The "How issues are related" paragraph says which follow-ups take the origin's milestone.
- **`docs/standard-changes.md`**: the capability label's sub-issue takes the needing issue's milestone because the
  needing issue waits for it. The commands don't change; the wording says why.
- **`scripts/dependabot_issues.py`**: an issue gets the release in progress as its milestone only when its pull request
  is a **security update**. A version update's issue gets none. A security update is told by the repository's
  Dependabot alerts, since the pull request looks the same either way (website #44, #46 and #54 were security
  updates, with the same branch, labels and title form as a version update). When the alerts can't be read, no issue
  opens in that repository and the run fails, rather than guessing.
- **The `troupe-run-dependabot` App** gains "Dependabot alerts: read", set by the owner on GitHub and declared in
  `oob/app-installations.json`, so the drift check holds it there.
- **A milestone-closing pull request lists the issues with no milestone.** When a plan closes a milestone, the plan's
  pull-request comment, and the plan of `main` the owner approves, list every open issue with no milestone in the
  milestone repositories that have issues (troupe, infrastructure and website). The review is then seen before the
  release closes. It only lists, and doesn't block.
- `docs/development-workflow.md`'s "Dependabot pull requests" says which issues get a milestone.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `org-profile`: the guide's "arose from" scenario reads the new follow-up rule, and a new requirement says what a
  milestone holds and that closing one starts a review of the issues with no milestone.
- `dependency-updates`: a Dependabot pull request's issue has the release in progress as its milestone only when it's a
  security update, told by the repository's open Dependabot alerts. Reading the alerts can fail the run like any other
  read.
- `dependabot-issue-credentials`: the App's permissions add Dependabot alerts read.
- `milestones`: a plan that closes a milestone lists the open issues with no milestone.

## Impact

- `org-profile/CONTRIBUTING.md` (delivered to troupe-run/.github by the next apply), `docs/standard-changes.md`,
  `docs/development-workflow.md`.
- `scripts/dependabot_issues.py` and `scripts/tests/test_dependabot_issues.py`. Fixtures use website's real alerts.
- A new script for the list, with its tests, and two steps in `.github/workflows/tofu.yml` (plan for a pull request,
  plan of `main`), reading with the job's own `GITHUB_TOKEN`, as `hook_modes.py` already reads troupe and website.
- `oob/app-installations.json`, and the App's permissions on GitHub (the owner's hand step, before the merge, so the
  first run after it can read alerts).
- Open Dependabot issues that already have `0.1.0` keep it until #230 re-sorts them. This change takes no milestone off
  an issue.
