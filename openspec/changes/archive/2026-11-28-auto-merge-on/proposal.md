# Proposal

## Why

Auto-merge (#359) has run in dry-run in troupe, infrastructure and website since 2026-11-20. The tally on #320 found
five merged pull requests it would have queued, none of them reverted or troubled after merging. The owner decided on
2026-11-28: "A: on everywhere + issue for refinements". This change is the follow-up #320's "Done when" asks for.

## What Changes

- `tofu/auto_merge.tf` sets `AUTO_MERGE` to `on` in troupe, infrastructure and website (was `dry-run`). The plan
  changes those three variables and nothing else.
- A test holds the switches at `on` in all three, so a later edit to one is a visible, reviewed change.
- The dry-run comment's text no longer speaks of "the dry-run week": `dry-run` stays a valid value for a repository
  that's switched back to it.
- The docs and the README say what the switch is set to now.
- #363: the token step drops `permission-actions-variables: read`, which `create-github-app-token` v3.3.0 doesn't
  take and ignores, and the workflow test's mapping from oob's declared permissions to inputs skips
  `actions_variables`, saying why.
- Not in this change: the refinements the owner asked for alongside (test-only additions over the size limit,
  narrowing infrastructure's `scripts/**` protection), which are infrastructure#427.

## Capabilities

### New Capabilities

### Modified Capabilities
- `auto-merge`: an added requirement that the switch is `on` in the three governed repositories.

## Impact

- `tofu/auto_merge.tf`: three `github_actions_variable.auto_merge` values change in place. The owner approves the
  plan, then main's apply; from the next run, a qualifying pull request is queued by `troupe-run-merge` instead of
  getting a "would have queued" comment.
- `.github/workflows/auto-merge.yml`, `scripts/auto_merge.py`, `scripts/tests/test_auto_merge_workflow.py`,
  `scripts/tests/test_auto_merge.py` (if it checks the comment text), `docs/development-workflow.md`, `README.md`.
- Break-glass is unchanged: setting `AUTO_MERGE` to `off` on GitHub stops it at once.
- Closes #320 and #363.
