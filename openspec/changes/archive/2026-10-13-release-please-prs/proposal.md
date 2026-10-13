## Why

troupe-run/troupe#23 (change `release-automation`, design D7) adds release-please to troupe. Its release pull request
has to pass the required `guard (workflow rules)` check like any other. Today it can't: release-please pushes to
`release-please--branches--main`, which matches no OpenSpec change, so `guard` fails every release PR on the
branch-change rule (#33). The same design asks for a PR-title check as a backstop (owner, 2026-10-13): squash merging
is off, so a title never becomes a commit today, but if squash is turned back on, the title becomes the commit
message and has to have been checked already.

## What Changes

- **A release-please branch passes the branch-change rule, narrowly.** In `guard.py ci`, a branch whose name starts
  with `release-please--` is exempt from the branch-change rule only when every commit it adds to `main` is authored
  by the release App's bot account, `troupe-run-release[bot]` (#34), and it adds at least one. Neither condition is
  enough alone: anyone can name a branch that way, and the author alone would exempt the App on any branch. The
  commit-message rule, and every other rule, still apply to those commits.
- **The exemption is closed until the App exists.** The bot account's email holds its user ID, which exists only once
  the owner creates the App. Until a single named constant in `guard.py` is filled in, no branch is exempt, so
  release PRs fail rather than pass on a guess.
- **The `guard` check reads a pull request's title as a commit message.** For a `pull_request` event, `guard.py ci`
  reads `pull_request.title` from the event payload and applies the `commit-message` rule to it, with a fix that says
  to edit the title. Release PRs are titled `chore: release main`, which passes.
- **Renaming a pull request re-runs the check.** `guard.yml` triggers on `pull_request` types `opened`, `edited`,
  `synchronize` and `reopened`.
- **`docs/development-workflow.md`** says both: the exemption in the `commit-branch-change` row, and the title in the
  `commit-message` row and the GitHub-check row.
- **Delivered to troupe.** `scripts/guard.py` and `.github/workflows/guard.yml` are delivered files, so the change
  reaches troupe by the usual delivery once the owner approves the plan.

No new rule ids: the title is checked under `commit-message`, and the exemption narrows `commit-branch-change`.

Not in this change: restricting commit scopes (troupe#23 design D8 keeps them free-form); the release App, its
environment, variable and labels (#34); release-please's config and workflow (troupe#23); filling in the bot's ID,
which follows #34 once the App exists.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: "The rules are re-checked on GitHub" names the release-branch exception to the branch
  rule. Two new requirements: "The release branch passes the branch rule, narrowly" and "Pull request titles are
  Conventional Commits".

## Impact

- `scripts/guard.py`: `run_ci` and `github_ci_inputs` (the exemption, the title, the commits a branch adds to
  `main`), and a constant for the release bot's author email.
- `scripts/tests/test_guard_push_and_ci.py`: tests for the exemption and the title.
- `.github/workflows/guard.yml`: the `pull_request` trigger types.
- `docs/development-workflow.md` and `openspec/specs/development-workflow/spec.md`.
- troupe-run/troupe receives `scripts/guard.py` and `.github/workflows/guard.yml` by delivery. The plan shows both;
  nothing else in the org changes.
