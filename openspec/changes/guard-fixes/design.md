# Design

## Context

See proposal.md for why. The three fixes are in `scripts/guard.py`, which is standard-library Python and is delivered
to troupe and website. Each is local to one function:

- `_only_uses_lines(root, sha, path)` reads `git diff-tree -p -U0 --no-commit-id --no-color <sha> -- <path>` and keeps
  every line starting `+` or `-` that doesn't start `+++` or `---`. Checked on git 2.56 in a scratch repository: a
  removed `---` line prints as `----`, so it's dropped.
- `dependabot_ineligibility(root, commits)` reads each commit's message with `git log -1 --format=%B`, and
  `non_dependency_paths` lists paths with `git diff-tree --no-commit-id -r -M --name-status <sha>`. In the same
  scratch repository, a merge commit that also added a file listed nothing, with or without `--first-parent`.
- `declared_labels(send)` builds a `urllib.request.Request` and calls `add_header("Authorization", …)`. urllib's
  `HTTPRedirectHandler.redirect_request` copies `req.headers` into the new request, and not `req.unredirected_hdrs`
  (CPython's `urllib/request.py`).

## Goals / Non-Goals

**Goals:**

- Each fix is the smallest change that closes its gap, with a test written first that fails on `main`'s guard.
- The existing tests pass unchanged: the fixes narrow what's exempt or sent, and nothing that passed for a real
  Dependabot update stops passing.

**Non-Goals:**

- Judging a merge commit's paths. A merge is refused outright, so `non_dependency_paths` doesn't need `-m`.
- Following, or refusing, redirects in the labels' read. The read still follows them, only without the token.
- Other findings from #194's look back.

## Decisions

### D1. Skip a diff's header lines by position, not by prefix (#204)

`_only_uses_lines` keeps a `+` or `-` line only inside a hunk: after an `@@` line and before the next `diff --git`
line. The `--- a/…` and `+++ b/…` headers come before a file's first `@@`, so they're skipped wherever they are, and
any content line counts, whatever it begins with. The issue offered this option.

Alternatives: matching the headers exactly (`--- a/<path>`, `+++ b/<path>`, `/dev/null`) depends on git's quoting of
unusual paths and `diff.noprefix`, and a content line could still equal one. Dropping only the first two `---`/`+++`
lines relies on the diff holding one file, which `-- <path>` gives today but nothing asserts.

### D2. A merge commit makes the branch ineligible (#205)

`dependabot_ineligibility` reads each commit's parents along with its message, and adds the reason
"`<sha7>` is a merge commit, and Dependabot doesn't make merge commits" for any commit with more than one parent. The
other reasons are still collected, so a refusal names everything that failed. The reason sits with the others, so the
refusal is the existing `commit-branch-change` one and says to take the update through an OpenSpec change.

Alternative: listing a merge's paths against its first parent (`diff-tree -m --first-parent`). That judges the merge
like a commit, but Dependabot never makes one, so any merge on a reserved branch is already wrong, and refusing it is
simpler and can't miss a path a merge resolution adds.

### D3. Add the token as an unredirected header (#206)

`declared_labels` adds `Authorization` with `request.add_unredirected_header`. urllib sends it on the first request
and leaves it off any request a redirect makes, to any host. `Request.get_header` and `has_header` read both kinds of
header, so the existing token test still sees it.

Alternative: a redirect handler that refuses a redirect to another host. That's more code, and a refused redirect
fails the read, which fails the rule. GitHub's contents API answers a renamed repository with a same-host redirect,
which then goes without the token: for this public file that only lowers the rate limit.

The test stubs `send`, as the other `declared_labels` tests do: the stub passes the request to urllib's own
`HTTPRedirectHandler().redirect_request` with another host's URL, which is what `urlopen` does on a 302, and records
the request it returns. Before D3 that request carries the token; after, it doesn't.

## Risks / Trade-offs

- [A same-host redirect loses the token] → the file is public and the token only raises the rate limit; a failed read
  fails the rule, saying so, rather than passing.
- [A legitimate Dependabot branch with a merge commit] → Dependabot rebases rather than merging; a person merging into
  its branch already makes it something Dependabot didn't write, so it takes an OpenSpec change.
- [Delivery reaches open pull requests] → a delivered rule judges an open pull request only once it rebases onto
  `main`. Before asking for the delivery plan's approval, the open Dependabot pull requests in troupe, infrastructure
  and website are checked for a merge commit or a workflow line that begins with `--` or `++` (task 4.2).

## Migration Plan

1. Merge, then the owner approves the delivery plan, which changes `scripts/guard.py` in troupe and in website.
2. Rollback: revert the commit; the next delivery restores the old file.
