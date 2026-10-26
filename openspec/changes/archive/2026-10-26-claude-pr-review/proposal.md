# Proposal

## Why

Nothing reviews a pull request in troupe, infrastructure or website before the owner does. The owner wants Claude to
review every one automatically, when it's opened and on each update, and to post its findings as review comments,
without ever committing or pushing (#154, owner, 2026-10-26). The repositories are public, so how the review gets its
credentials, and what a run can write, has to be settled before any workflow exists.

## What Changes

- A new workflow, `.github/workflows/claude-review.yml`, runs `anthropics/claude-code-action` on `pull_request`
  (opened, synchronize, reopened, ready_for_review). Drafts are reviewed too (owner, 2026-10-26).
- **Comments come from our own review App, `troupe-run-review[bot]` (owner, 2026-10-26, design D1).** The App has
  only "Contents: read" and "Pull requests: write", and the run mints its token for the run's repository with exactly
  those. Anthropic's Claude GitHub App isn't used: the action asks it for a token that can write contents, whatever
  the workflow's `permissions:` say. The run's own `GITHUB_TOKEN` keeps `contents: read` and gets no `id-token`. This
  replaces #154's "install the Claude App" step with creating our own App by hand, as the release, board and docs
  Apps were. Its installation is declared in `oob/app-installations.json`. (The first version wrote through
  `GITHUB_TOKEN`, so every comment came from `github-actions[bot]`. The owner found that blurred where they came
  from.)
- Two credentials, each an org Actions secret visible to troupe, infrastructure and website only, set by the owner
  from 1Password and recorded in `oob/README.md`: `CLAUDE_CODE_OAUTH_TOKEN`, made with `claude setup-token`, and the
  review App's key, `REVIEW_APP_PRIVATE_KEY`. OpenTofu never holds them (owner, 2026-10-26, design D3).
- Pull requests opened by a bot are skipped: Dependabot, release-please's release PRs through `troupe-run-release`,
  and any App's. A fork's pull request gets no secrets on `pull_request`, so it isn't reviewed. Both are accepted.
- What the review checks is written once, in the workflow's prompt: the repository's `CLAUDE.md` (which the action
  reads from the base branch), the org guide, the OpenSpec change's tasks and specs against the diff, the issue's
  "Done when", and Conventional Commits. Claude's tools are limited to reading the pull request and commenting on it.
- The workflow is delivered to troupe and website with the guard's files (`guard_files` in `tofu/guard_delivery.tf`).
  This repository's copy is the source, so the delivered-file rule protects the copies.
- It's advisory: it's not added to `tofu/required-checks.json`.
- **.github is left out (owner, 2026-10-26).** Its only pull requests are the App's, and those are skipped. This change
  records on #136 that nothing here needs Actions on `.github`.

## Capabilities

### New Capabilities
- `pr-review`: Claude's automatic review of pull requests in the governed repositories. Covers when it runs and which
  pull requests it skips, what a run may write, which credential it uses and where it can be read, what the review
  checks against, and how the workflow reaches each repository.

### Modified Capabilities
<!-- None. The guard-delivery requirements already cover every file in guard_files, so the review workflow is
     delivered, listed and protected without a requirement changing. -->

## Impact

- `.github/workflows/claude-review.yml`: new. One job, `review`, with `anthropics/claude-code-action` pinned to a full
  commit SHA, as the other actions here are.
- `tofu/guard_delivery.tf`: the workflow joins `guard_files`. The plan shows a new file and a changed
  `.github/guard-delivery.json` in each of troupe and website, so four changes in all.
- `scripts/tests/test_claude_review_workflow.py`: new. Pins the trigger, the bot skip, the permissions, the token
  input, the secret's name, the allowed tools and the pinned action.
- `oob/README.md`: a new section on the review App and the Claude token: how each is made, set, checked by name and
  rotated. `oob/app-installations.json`: the review App's installation.
  `README.md` (layout table) and `docs/development-workflow.md`: the new workflow, and a note that it's advisory.
- GitHub, by hand (owner): create the review App and install it on the three repositories, create the Claude token,
  store both in 1Password, and set both org secrets with "selected repositories".
- troupe and website: no change by pull request. The workflow arrives by delivery, after the owner approves the plan.
- #154: its install step and its "Done when" change. Our own review App is installed instead of the Claude App, and
  `.github` is left out. #136
  gets a comment saying the review doesn't need Actions on `.github`.
