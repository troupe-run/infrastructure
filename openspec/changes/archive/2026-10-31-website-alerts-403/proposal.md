# Proposal

## Why

Since #235 (needed-for-milestones), `dependabot-issues` reads a repository's open Dependabot alerts to tell a security
update from a version update. Its first scheduled run on `main` failed for website with HTTP 403 "Resource not
accessible by integration" (#238), and every daily run will fail the same way until it's fixed. Meanwhile no issue
opens or is relinked in website, so a new Dependabot pull request there gets no issue, and a security update's issue
wouldn't get the release's milestone. (Website's one open Dependabot pull request, #55, already has its issue from
before #235.)

The cause is in the workflow, not on GitHub. The `issues` job mints the `troupe-run-dependabot` App's token with
`permission-issues: write` and `permission-pull-requests: write`. `actions/create-github-app-token` gives a token only
the permissions it's asked for once any are listed, so the token lacks "Dependabot alerts: read", although the App and
its installation have it (`oob/app-installations.json`, checked by the drift check). The failed run's log shows the
step asking for those two only. Website is the only repository that failed because the script reads alerts only when
a repository has an open Dependabot pull request, and today only website has one (troupe and infrastructure have
none, so they reported "nothing to do"). #235 didn't catch it: its local run (task 2.4) used the owner's login, which
can read alerts, and `scripts/tests/test_dependabot_issues_workflow.py` pins the token's permissions to the old pair
by hand, so it passed unchanged.

## What Changes

- **`.github/workflows/dependabot-issues.yml`**: the `issues` job's token also asks for
  `permission-vulnerability-alerts: read`, so it has every repository permission the App is declared with.
- **`scripts/tests/test_dependabot_issues_workflow.py`**: the permissions the `issues` token must ask for are read
  from the App's declaration in `oob/app-installations.json` (each declared permission but `metadata`, which every
  token has), not written out by hand. A permission added to the App without the workflow asking for it, or one the
  workflow asks for that the App isn't declared with, fails `scripts/check.py`, naming it.
- The workflow's header comment says the token asks for the App's declared permissions.
- After the merge, a run of `dependabot-issues` on `main` reads website's alerts and passes, which closes #238.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dependabot-issue-credentials`: a new requirement says the token the workflow mints asks for exactly the App's
  declared repository permissions, checked against the declaration by `scripts/check.py`, so a run can read
  everything the App was given for it.

## Impact

- `.github/workflows/dependabot-issues.yml` (one input on the token step, and its comment).
- `scripts/tests/test_dependabot_issues_workflow.py` (the pinned permissions become derived ones).
- No OpenTofu change, no plan to approve, and nothing the owner changes on GitHub: the App and its installation
  already have the permission.
- Out of scope: the other workflows that mint App tokens (`board`, `dependabot-dispatch`, `release`, `docs`, review)
  keep their hand-pinned permission tests. Some of them deliberately ask for less than their App has, so deriving
  theirs needs its own look; that's a separate issue if the owner wants it.
