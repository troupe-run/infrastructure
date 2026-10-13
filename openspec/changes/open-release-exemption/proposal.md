## Why

troupe's release pull requests have to pass the required `guard (workflow rules)` check (troupe-run/troupe#23). #33
built the exemption that lets them: a `release-please--` branch whose commits are all the release App's bot's skips
the branch-change rule. It's closed, because `RELEASE_AUTHOR_EMAIL` in `scripts/guard.py` is `None`, and #33 said to
fill it only once GitHub, not the guard, decides who writes those branches. That's now true on troupe: #34's
`release branches` ruleset is applied (#41, run 38408104046), with the release App as its only bypass actor and no
owner bypass. So the exemption can open (#42).

## What Changes

- **The constant is filled:** `RELEASE_AUTHOR_EMAIL = "341990208+troupe-run-release[bot]@users.noreply.github.com"`,
  from `gh api 'users/troupe-run-release%5Bbot%5D' --jq .id` (341990208, checked 2026-10-13). Its docstring says why
  it's safe now: the ruleset is the hard check, and the author check alone isn't.
- **The exemption applies only in a repository whose release branches GitHub reserves for the App.** Today that's
  troupe alone. The guard also runs here, in `troupe-run/infrastructure`, which has no such ruleset: filling the
  constant without this would let anyone push a `release-please--` branch here with the bot's address written into
  `--author` and skip the branch rule, with nothing behind the author check. This wasn't in #42's text; it follows
  from its reason ("the ruleset is the hard check"), and the owner chose it on 2026-10-14. See design D1.
- **The repository is where the branch lives.** For a push it's the repository GitHub names for the run; for a pull
  request it's the head repository, so a fork's `release-please--` branch, which troupe's ruleset doesn't cover, is
  never exempt (owner, 2026-10-14). A run that can't name it (a local dry run without one, or a deleted fork) exempts
  nothing, and a payload whose head repository is present but unreadable is an error, as an unreadable title is.
- **`None` stays possible, as the rollback.** The constant keeps its `str | None` type, and `None` still exempts
  nothing, so closing the exemption again is a one-line change.
- **A test ties the guard to the ruleset.** It fails if `tofu/release.tf` stops declaring the `release branches`
  ruleset for each repository the guard exempts, so removing the ruleset can't leave the exemption open unnoticed.
- **Docs:** `docs/development-workflow.md`'s `commit-branch-change` row and its known gap, and the README's release
  ruleset paragraph, say the exemption is open, where, and why it's safe.
- **Delivered to troupe**, like any guard change: CI green on all three OSes, then the owner approves the plan.

Not in this change: release-please's config and workflow (troupe-run/troupe#23); the same author-trust gap in
`delivered-file` (#35); the ruleset itself (#34, done); a release ruleset on any other repository.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: "The release branch passes the branch rule, narrowly" is limited to repositories where
  GitHub reserves `release-please--*` branches for the release App (a pull request's head repository, so not a
  fork), and a check that can't name that repository exempts nothing.

## Impact

- `scripts/guard.py`: `RELEASE_AUTHOR_EMAIL` filled; a constant naming the repositories the
  exemption applies in; the repository passed from the GitHub event into the exemption; a `--repository` option on
  `guard.py ci` for a local dry run.
- `scripts/tests/test_guard_push_and_ci.py`: the exemption's tests use the real address and a repository; new tests
  for another repository, a fork, none, and an unreadable head repository; a test that the ruleset is declared for each exempt repository.
- `docs/development-workflow.md`, `README.md`, `openspec/specs/development-workflow/spec.md`.
- troupe-run/troupe receives `scripts/guard.py` by delivery. The plan shows that file's delivery and nothing else.
