# Proposal

Issue: #8 (part of #1). Decisions by the owner on 2026-10-12 are recorded in #8's comments and in design.md.

## Why

The rules for how the org builds software, the `development-workflow` spec and its guard, live in troupe, the
product, although the spec says of itself that they "govern how troupe is built; they are not features of troupe"
(Decision #25). This repo doesn't follow them at all yet: it runs the workflow by hand. Moving them here gives one
source for the rules, governs this repo too, and makes troupe receive the guard rather than maintain it.

## What Changes

- **The `development-workflow` spec moves here,** reworded to govern every repository the org builds in that receives
  the guard (`troupe` and this one), rather than "this repository".
- **The guard moves here and governs this repo:**
  - `scripts/guard.py` and its tests;
  - `.githooks/`;
  - the Claude Code hooks in `.claude/settings.json`;
  - the `guard` GitHub workflow;
  - `scripts/check.py` turning the hooks on, as troupe's does.

  From the merge of this change, this repo's copy is the only one anyone edits.
- **The guard's tests run on Linux, macOS and Windows here.** Everything else in CI stays on Linux.
- **The guard is delivered to troupe as files, by the App, straight to `main`.** OpenTofu declares troupe's copies of
  the guard's files as `github_repository_file` resources whose source is this repo, as it already does for
  `.github`. So:
  - every delivery is a plan the owner approves;
  - a hand edit in troupe shows as drift.
- **troupe's "protect main" ruleset gains a bypass for the infrastructure App,** so that delivery can push. The owner
  and agents are still refused a direct push.
- **A new rule, `delivered-file`:** in a repository that receives the guard, a commit or edit that changes a
  delivered file is refused, and the `guard` check fails on one not made by the App. The fix is to change the file
  here.
- **Fix the stale delivery commit message** (an adopt-org finding). Each commit into `.github` or troupe names the
  file and the content it delivers. Today an update reuses the previous commit's message.
- **The workflow rules' human-readable form** becomes `docs/development-workflow.md` here, linked from the org's
  `CONTRIBUTING.md`.
- **A matching troupe change** (its own issue, change and PR) removes troupe's spec, the guard's tests and its
  rules doc, and links to this repo instead.

Out of scope:
- making `guard` a required check (`required-checks`);
- applying from CI (#6);
- the website repo, which has no OpenSpec changes or `scripts/check.py` to govern yet;
- automating the delivery when the guard changes. Delivery is a plan and apply, like any other change to the org.

## Capabilities

### New Capabilities

- `development-workflow`: the rules for how every governed repository is developed, the guard that enforces them,
  and how an override is granted. Moved from troupe and reworded.
- `guard-delivery`: how the guard reaches the repositories it governs: this repo as the single source, delivery by
  the App, drift shown in the plan, and delivered files not edited where they land.

### Modified Capabilities

- `rulesets`: "Changes reach main only through a pull request" gains one exception. The infrastructure App may push
  the guard's delivered files straight to `main` in a repository that receives them.
- `org-profile`: each sync commit into `.github` names the file and the content it writes, instead of reusing an
  earlier message.

## Impact

- **New here:** `scripts/guard.py`, `scripts/tests/test_guard_*.py`, `.githooks/`, `.claude/settings.json`,
  `.github/workflows/guard.yml`, `docs/development-workflow.md`, `CLAUDE.md`, and `tofu/guard_delivery.tf` (which also
  generates troupe's `.github/guard-delivery.json`, the list of delivered files).
- **Changed here:**
  - `scripts/check.py` (it turns the hooks on);
  - `.github/workflows/ci.yml` (a three-OS job for the guard's tests);
  - `tofu/modules/repository` (an optional App bypass);
  - `tofu/org_profile.tf` (the commit message);
  - `org-profile/CONTRIBUTING.md`;
  - `README.md`;
  - `openspec/config.yaml` (the "never direct commits to a product repo" constraint now names this exception).
- **GitHub:**
  - commits by the App to troupe's `main`, one per delivered file;
  - a bypass entry on troupe's ruleset.
- **The App needs Workflows write** to change troupe's `.github/workflows/guard.yml`. The owner grants it on the App,
  and `oob/app-installations.json` records it.
- **troupe:** the matching change, which has to merge before a delivery changes `guard.py`'s behaviour. Otherwise
  troupe's old tests would fail against the new guard.
- **This repo's own workflow:** from this change on, commits here go through the hooks, including the full check
  before each commit.
