# Design

## Context

The `issues` job of `.github/workflows/dependabot-issues.yml` mints the `troupe-run-dependabot` App's token with
`actions/create-github-app-token`, listing `permission-issues: write` and `permission-pull-requests: write`. The
action's README (v3.3.0, the pinned commit): "By default, the token inherits all of the installation's permissions";
once any `permission-*` input is given, the token gets only those. Its `action.yml` has a
`permission-vulnerability-alerts` input ("read" or "write").

The App's declaration, `oob/app-installations.json`, gives it `issues: write`, `metadata: read`,
`pull_requests: write` and `vulnerability_alerts: read`, and the drift check (`scripts/oob.py`) holds the installation
to it. So the installation can read alerts; the token the workflow asks for can't.

`scripts/dependabot_issues.py` reads `repos/<org>/<repo>/dependabot/alerts?state=open` only for a repository with an
open Dependabot pull request. On 2026-10-31 that was website alone (#55, typescript 6.0.3 → 7.0.2), so only website
failed. The run before #235 merged, on 2026-10-30, didn't read alerts at all.

`scripts/tests/test_dependabot_issues_workflow.py` checks the token with `token_problems(..., granted)`, where
`granted` is written out by hand as `{"permission-issues": "write", "permission-pull-requests": "write"}`.

The `dependabot-issues` environment deploys only from `main`, so no run on the branch can mint the App's token: the
fix can be shown working only by a run on `main` after the merge.

## Goals / Non-Goals

**Goals:**

- The `issues` token can read Dependabot alerts in the three repositories, so a run handles website again.
- The token's permissions can't fall behind, or run ahead of, the App's declaration without `scripts/check.py`
  failing.

**Non-Goals:**

- Changing the App, its installation or its declaration. They're already right.
- The other workflows' App tokens (`board`, `dependabot-dispatch`, `milestones-notice`, `schedules`, `tofu`,
  `claude-review`). Several ask for less than their App has on purpose, such as `tofu`'s read-only plan token, so
  "ask for all the App has" isn't their rule.
- Changing how `dependabot_issues.py` reads alerts or handles a failed read. Its refusal worked as specified
  (dependency-updates: "A run that can't read a repository's alerts opens no issue there").

## Decisions

**D1. Ask for the permission explicitly, rather than listing none.** Dropping every `permission-*` input would also
fix it, since the token would inherit the installation's permissions. But then the token would carry whatever the
installation gains by hand, until the next drift check notices it, and the workflow file would no longer say what the
token can do. Listing `permission-vulnerability-alerts: read` keeps the token at what the workflow declares, which is
also what the action recommends.

**D2. The test reads the expected permissions from the App's declaration.** `granted` for the `issues` token becomes
the App's entry in `oob/app-installations.json`, without `metadata` (every installation token has it, and the action
has no input for it), each key turned into its input name (`vulnerability_alerts` → `permission-vulnerability-alerts`)
with the declared level. A hand-written copy is what let #235 add the permission to the App and miss the token: the
test passed unchanged. Deriving it means the next permission added to the declaration fails the check until the
workflow asks for it, and a permission the workflow asks for beyond the declaration fails too. The failure names each
permission and which side has it, so the fix is plain. The board token's `granted` stays hand-written (Non-Goals).

The test fails, rather than skipping, if the App's entry is missing from the declaration or has no permissions: an
empty expectation would pass a token that asks for nothing.

**D3. Prove the derived check fails for the bug it's for.** Before the workflow change, the derived test fails on
this branch, naming `permission-vulnerability-alerts`; after it, the test passes. A mutation case also removes the
input from a copy of the workflow and expects the failure, so the test can't quietly stop checking it.

**D4. The fix is verified on `main`.** After the merge, a `dependabot-issues` run on `main` must read website's
alerts and pass. Website's only open Dependabot pull request today, #55, is typescript, which has no open alert, so
the expected result is `troupe-run/website: nothing to do` (or a relink if Dependabot has moved on), with no 403.
A run by hand (`gh workflow run dependabot-issues`) writes issues as every run does, so it's the owner's call whether
to start one or wait for the daily schedule, which runs hours late.

## Risks / Trade-offs

- **Another cause behind the first one.** If website's alerts were also refused for a reason the token's permissions
  don't explain, the run on `main` would still fail. Nothing found points that way: the App's installation has the
  permission and covers website, and the owner's login read website's alerts on 2026-10-30. If it does fail, the
  error is raised with the owner before #238 is treated as done.
- **The declaration becomes the test's input.** A wrong declaration now yields a wrong expectation. The drift check
  already compares the declaration with the installation, so the two together tie the token to what GitHub has.
