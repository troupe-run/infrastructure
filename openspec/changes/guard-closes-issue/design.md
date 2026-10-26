# Design

## Context

See proposal.md for why. Current state, read on 2026-10-26 at infrastructure `472ee1e`:

- **The local rule.** `pr_closes_issue` in `scripts/guard.py` judges an agent's `gh pr create`: it finds the
  description in `--body`/`--body-file` and passes when `CLOSING` matches it. `CLOSING` is one compiled pattern:
  `close[sd]?`, `fix(e[sd])?` or `resolve[sd]?`, an optional `:`, whitespace, then `#n`, `owner/repo#n` or an issues
  URL, case-insensitive. That is GitHub's own list of closing keywords. The rule id `pr-closes-issue` is in
  `OVERRIDABLE_RULES`.
- **The GitHub check.** `github_ci_inputs` reads, for a `pull_request` event, the title and the head repository from
  the payload at `GITHUB_EVENT_PATH`, and returns `(base, head, branch, title, repository)`. A title that isn't a
  string raises `UnreadableTitleError`, which `run_ci_entry` reports as a refusal saying to re-run. A push returns
  no title. `run_ci` checks the title (`pr_title`) when it's not `None`, and exempts a release branch from the branch
  rule with `reserved_release_branch(branch, repository)`. The `ci` subcommand takes `--title` for a local run.
- **The workflow.** `guard.yml` runs on `pull_request` types `opened, edited, synchronize, reopened`, so editing a
  description already re-runs it. It needs no change beyond its header comment.
- **The payload.** GitHub's `pull_request` object always carries `body`: a string, or `null` when the description is
  empty.
- **Open pull requests, 2026-10-26** (each repository's `gh pr list`, matched with `CLOSING`): troupe #89
  (`release-please--branches--main`, no closing line); infrastructure #176 (closes); website #52 (closes), #44, #45,
  #46 (Dependabot, no closing line, already failing `commit-branch-change`).

## Goals / Non-Goals

**Goals:**
- One reading of "closes an issue", the same locally and on GitHub.
- A pull request opened by any route meets the rule before it can merge (`guard` is a required check).

**Non-Goals:**
- Whether the line will actually close the issue. GitHub closes it only when the pull request merges into the default
  branch, and only if the issue exists and the merger can close it. The guard reads text, as the local rule does.
  Checking the issue exists would need the network and another repository's permissions for a cross-repository close.
- Pushes. A push to `main` (the App's state commits and deliveries) or to a branch isn't a pull request, and has no
  description.
- Dependabot. Its pull requests fail the rule, as they fail the branch rule today; #170 sections 2-4 give them an
  issue and an exemption.

## Decisions

### D1. The same rule id, `pr-closes-issue`, and the same pattern

The GitHub refusal is under `pr-closes-issue`, as `pr_title`'s is under `commit-message`: one rule, enforced in two
places, with one row in the rules doc. It uses `CLOSING` unchanged, so local and GitHub can't disagree about what
closes an issue. The id stays in `OVERRIDABLE_RULES` for the local hook; on GitHub no override is consumed, as for
every other rule the check re-applies.

Rejected: a new GitHub-only rule id. The two would mean the same thing under different names. Rejected: GitHub's
`closingIssuesReferences` from the API. It needs a token with the right scope and a network call, misses a
cross-repository issue the token can't see, and could disagree with what the local rule accepted.

### D2. Read the description beside the title, and check it in `run_ci`

`github_ci_inputs` also returns the pull request's description: the `body` string, or `""` for `null`. For a push it
returns `None`, as for the title. `run_ci` gains a `description: str | None = None` parameter and, when it isn't
`None`, appends a new `pr_description(description)` decision after the title's, unless
`reserved_release_branch(branch, repository)` holds (D4). The `ci` subcommand gains `--description`, for a local run,
like `--title`.

The refusal: problem `pull request '<title>' doesn't close an issue: its description has no closing line.` (or `has
no description` for `""`); fix `Edit the description (gh pr edit <n> --body-file <file>, or on GitHub) to add a line
like 'Closes #22', or 'Closes owner/repo#22' for an issue in another repository. Editing it re-runs this check.` The
title names the pull request in the log; the run's page names its number.

`None` for "not a pull request" and `""` for "empty description" are kept apart, so a push is never refused for
having no description, and an empty description never passes.

Rejected: growing the five-element tuple into a dataclass in this change. It's the clearer shape, but it's a refactor
of every call site and test, and isn't needed for #173. Noted as a possible follow-up, not done here.

### D3. An unreadable description fails the check

A `pull_request` payload whose `body` key is missing, or is neither a string nor `null`, raises
`UnreadableDescriptionError`, reported by `run_ci_entry` under `pr-closes-issue` with the same "re-run; if it fails
again, tell the owner with the run's URL" fix as an unreadable title. A missing key is malformed, not "no
description": GitHub always sends it, so treating its absence as empty would refuse with the wrong reason, and
treating it as passing would skip the rule (malformed input is an error, never a fall-through).

The existing CI-entry tests write payloads with only a `title`. They gain a `body`, so they keep testing what they're
named for rather than failing on this rule.

### D4. release-please's exemption is the branch exemption

release-please's pull request closes no issue: it releases what other pull requests closed. It's exempt exactly when
its branch is exempt from the branch rule, using `reserved_release_branch` with the head repository: a
`release-please--` branch in a repository whose ruleset reserves the prefix for the release App (troupe). A fork's
branch of that name, or one in infrastructure or website, isn't exempt. One function decides both, so the two
exemptions can't drift apart.

Rejected: exempting by the pull request's author (the release App's user in the payload). It would be a second test
for the same exemption, and the guard keys release-please's exemption on what a ruleset enforces, the reserved branch
name, not on who appears to have acted (drop-forgery-resistance design D1, #47).

### D5. Delivery without surprises

Once delivered, every open pull request without a closing line in troupe and website goes red; infrastructure's go red
once this merges. Before asking for the delivery plan's approval, list each governed repository's open pull requests
and match them with `CLOSING` (the command in Context). Fix any that isn't exempt and isn't Dependabot's by adding its
closing line, or tell the owner when the issue it should close isn't clear. Dependabot's are already red and stay
#170's to settle. Record the list in tasks.md.

## Risks / Trade-offs

- [A pull request that legitimately closes nothing, such as a revert or a docs fix with no issue] → the owner's rule
  is that every pull request closes a ticket; open one. The owner can't override on GitHub, by design: the check is
  required and consumes no override.
- [A closing keyword in prose that GitHub wouldn't act on, such as inside a code block] → passes, as it does locally.
  The rule checks intent is stated, not GitHub's linking.
- [Dependabot pull requests gain a second refusal] → they can't merge today either; #170 changes both.
- [The delivered guard reaches troupe and website at the owner's apply, not at merge] → infrastructure is checked from
  this pull request on (its CI runs the branch's `guard.py`), the others from the delivery. D5's list is re-run just
  before the plan's approval.

## Migration Plan

1. Merge; infrastructure's own pull requests are checked from the next run.
2. Re-run D5's list, fix what's needed, then approve the delivery plan for troupe and website.
3. Rollback: revert the commit and deliver again; the rule has no state.
