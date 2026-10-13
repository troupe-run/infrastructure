## Context

`guard.py ci` (`run_ci`) checks one range of commits: for a pull request, from the merge base with the base branch to
the head; for a push, from the event's `before` to the head. Over that range it applies the commit-message rule, the
archived-tasks rule and, in a repository that receives the guard, the delivered-file rule, and it applies the
branch-change rule to the branch name. `guard.yml` runs it on every push to every branch and on `pull_request` with
the default types. Both runs report as `guard (workflow rules)`, a required check in troupe and here.

release-please (troupe#23 design D4, D5) keeps one commit on `release-please--branches--main`, `chore: release
main`, made through the API with the release App's token, and force-pushes the branch whenever `main` moves. Commits
made that way are authored by the App's bot account, `troupe-run-release[bot]`, whose noreply email holds its numeric
user ID: `<id>+troupe-run-release[bot]@users.noreply.github.com`. The App doesn't exist yet (#34):
`GET /users/troupe-run-release[bot]` returns 404 on 2026-10-13.

The guard already trusts one bot by its author email: `DELIVERY_AUTHOR_EMAIL` for the delivered-file rule.

## Goals / Non-Goals

**Goals:**
- release-please's PR, and the pushes to its branch, pass `guard` without an override.
- Nothing else gets past the branch-change rule that doesn't today.
- A PR title is checked under the same rule as a commit message, whatever merge method is on.

**Non-Goals:**
- Proving who made a commit in the guard. An author email is self-declared, and so, for commits made through the
  API, is the "Verified" badge's link to an author. Who may write a release branch is enforced by GitHub instead
  (D5); the guard's check is the honest-mistake check behind it.
- Refusing `fixup!`/`squash!` titles. The title gets exactly the commit-message rule, which accepts them when they
  name a Conventional subject, as it does for commits that land by rebase.
- Checking titles outside GitHub. Locally there's no pull request yet; `gh pr create` stays governed by
  `pr-closes-issue` only.

## Decisions

### D1. The exemption judges the commits the branch adds to `main`

For a branch whose name starts with `release-please--`, the guard lists the commits reachable from the head and not
from `origin/main` (`git rev-list <head> --not origin/main`), and exempts the branch from the branch-change rule when
that list is non-empty and every commit's author email equals `RELEASE_AUTHOR_EMAIL`. Every other rule still runs
over the usual range, unchanged.

Why not the event's range: when `main` moves, release-please rebuilds its commit on the new `main` and
force-pushes. The push event's range (`before..head`) then holds the new `main` commits too, which other people
authored, so the push run would fail the branch rule and put a red `guard (workflow rules)` on the release PR's head.
What the branch adds to `main` is the same set for a push and a pull request, and it's what the rule is about. The
workflow already fetches every branch (`fetch-depth: 0`), so `origin/main` is there.

The empty case fails: a branch that adds nothing has nothing the App wrote, and a vacuous "every commit" would
exempt it. If `origin/main` can't be resolved, the branch isn't exempt.

Alternatives: the event's range (fails on every force-push, above); matching the full name
`release-please--branches--main` (release-please names branches per target and component, so the prefix the issue
names is the stable part, and the author condition is what narrows it).

### D2. The bot is named by one constant, closed until it's filled

`RELEASE_AUTHOR_EMAIL: str | None = None` sits next to `DELIVERY_AUTHOR_EMAIL` in `guard.py`, with a docstring saying
it's filled from `GET /users/troupe-run-release%5Bbot%5D` once the App exists. While it's `None`, no branch is
exempt, so a release PR fails on the branch rule and says why. That's the choice that can't let anything through by
guessing; troupe's release workflow merges last (troupe#23), so nothing is blocked in the meantime.

The email, not the name: a name is free text, while the email carries the account's numeric ID, and it's the form
`DELIVERY_AUTHOR_EMAIL` already uses.

Filling it in is a one-line follow-up after #34, through its own change and delivery. It isn't a task here, because
this change can't be archived while waiting on the owner to create the App.

### D3. The title is read from the event payload and checked by `commit_message`

`github_ci_inputs` returns the title as well: for a `pull_request` event, `pull_request.title` from
`GITHUB_EVENT_PATH`. `run_ci` takes `title: str | None`; when it's given, a new `pr_title(title)` applies
`commit_message` to it and, if refused, returns a `commit-message` decision whose problem names the title ("pull
request title '<title>' isn't a Conventional Commit") and whose fix says to edit the title (`gh pr edit <n> --title
'<type>(<scope>): <subject>'`, or the title field on GitHub) and lists the types. The commit fix (`git commit
--amend`) would be wrong for a title.

A `pull_request` event whose payload has no string title is malformed input, not "no title": the check fails, saying
it couldn't read the title. GitHub always sends one, so this only fires when something is genuinely wrong.

`guard.py ci` gains `--title`, alongside `--base`, `--head` and `--branch`, so a run can be reproduced locally.

No new rule id: a title is checked as a commit message, and the docs' table lists rule ids exactly
(`test_guard_docs.py`).

### D4. `guard.yml` re-runs on title edits

`pull_request: types: [opened, edited, synchronize, reopened]`. `edited` also fires for a body or base-branch edit;
the run takes seconds, and a base change does need a re-check. The concurrency group (`guard-pull_request-<ref>`)
already cancels a superseded run.

This also applies to this repository: from the merge on, its own PR titles are checked.

### D5. GitHub enforces who writes a release branch; the guard checks behind it

Anyone can write the bot's email into a commit (`git commit --author`), and creating the App doesn't change that. So
the name and the author together are no stronger than either alone against someone doing it on purpose. The
"Verified" badge doesn't close it either: API-made commits are signed with GitHub's general key, not one per App, and
checking it would need an API call from a guard that works offline.

What closes it is a ruleset on troupe over `refs/heads/release-please--*` that restricts creation, update and
deletion, with the release App as the only bypass actor (`Integration`, `always`). Then only the App can write a
branch with that name, and the name is the proof. The org already runs one of this shape: `app only` on
`troupe-run/.github` restricts update and deletion with the infrastructure App as the only bypass, on GitHub Free. The
`creation` rule isn't used anywhere yet, so #34 probes it on a throwaway repository first. The ruleset has no
`non_fast_forward` rule, because release-please force-pushes; as the bypass actor it isn't held to one anyway.

The ruleset belongs to #34, not here: #34 declares everything else about the App, and the bypass entry needs the
App's ID, which exists only once the owner creates it. Until both land, the exemption stays closed (D2), so the gap
can't be used in the meantime. The docs' known gaps say this (task 4.1).

Alternatives: checking `verification.verified` through the API in CI (forgeable as above, and the guard goes online);
checking the event's `sender` (an `edited` event sent by the App says nothing about who pushed the commits on the
branch).

## Risks / Trade-offs

- [A forged author email on a `release-please--` branch skips the branch rule] → Once #34's ruleset is on (D5),
  nobody but the App can push such a branch. Before then, the exemption is closed (D2). Even if it were open, it
  would skip only that rule; every other rule, review and the required checks still apply.
- [#34 fills `RELEASE_AUTHOR_EMAIL` before its ruleset is on] → The follow-up that fills the constant is ordered
  after the ruleset is applied, and says so (tasks, workflow follow-up).
- [release-please makes its commit with another identity than the App's bot (e.g. a configured author)] → troupe#23
  design D9 sets only `signoff`; the first real release PR shows the author. If it differs, the constant names that
  identity instead, in the follow-up that fills it.
- [`edited` runs leave several `guard (workflow rules)` runs on one head SHA] → The earlier failure stays on the
  commit and in the PR's check rollup, but a required check follows the latest run: the probe (task 5.1) showed a
  renamed PR go `CLEAN`, and `BLOCKED` again when renamed back to a bad title.

## Migration Plan

Merged here, the owner approves the `apply` job, and the App delivers `scripts/guard.py` and `.github/workflows/guard.yml`
to troupe. Open PRs in troupe pick up the new workflow on their next event. Rollback is reverting the commit here and
delivering again. Once #34 creates the App, a follow-up change fills `RELEASE_AUTHOR_EMAIL` and delivers it.
