# Design

## Context

See proposal.md for the four corrections and why they're batched. Two of them change the guard; the other two are
wording and need no design.

**The index.** While a hook runs, git sets `GIT_INDEX_FILE` to the index it is committing: `.git/index` (relative)
for a plain commit, `.git/index.lock` for `git commit -a`, `.git/next-index-<pid>.lock` for `git commit <path>`.
`_git_env()` strips it, with the other repository-location variables, from every nested git call. That way the guard's
tests, run from inside a hook, don't inherit it. `protocol-schema-commit-types` D4 added `committing_paths`, the one
read that puts it back, but only the commit-msg hook uses it. The pre-commit hook still reads `.git/index` in five
places: `run_pre_commit`'s staged list, `ReadStaged` (used for archived `tasks.md`, the delivery list and
`scripts/check-paths.toml`), and `commit_checks`' `git diff --name-only` and `git diff --cached`.

**The push range.** `github_ci_inputs` takes a push payload's `before` as the base, and falls back to the merge-base
with `origin/main` only when `before` is missing or all zeros. After a force push, `before` is the replaced tip. The
`actions/checkout` clone (`fetch-depth: 0`) only has commits some ref reaches, so the replaced tip is missing.
`commits_in_range` then gets a failing `rev-list` and falls back to `rev-list <head> --not --remotes`. That's empty,
because `head` is on its own remote-tracking branch. Pull requests aren't affected (their base is a merge-base).

## Goals / Non-Goals

**Goals:**
- Every pre-commit read judges the index git is committing, from one helper, so it can't be fixed in one place and
  missed in another.
- A push run whose `before` isn't in the clone judges the branch since it left `main`, and says so.

**Non-Goals:**
- The pre-push hook's range. The replaced tip is still on the local remote-tracking ref when the hook runs, so
  `remote..local` resolves; nothing was reported there.
- A force push whose `before` *is* in the clone keeps today's `before..head` range. The existing test
  `test_a_release_branch_rebuilt_on_a_newer_main_passes_on_the_force_push_range` pins it.
- `commits_in_range`'s own `--not --remotes` fallback. It stays for the pre-push hook's first push, where it's right.
- `scripts/check.py` keeps running with `GIT_INDEX_FILE` stripped. Its tests make their own repositories.

## Decisions

### D1. One environment for "the index being committed"

Add `_committing_env(root)`: `_git_env()` plus `GIT_INDEX_FILE` when git set one, resolved against `root` (git gives
it relative for a plain commit). `committing_paths` is rebuilt on it, and so is a `ReadStaged`. `commit_checks` uses
it for both of its diffs. `run_pre_commit` takes its staged list from `committing_paths` (so `--no-renames` there
too, as `commit_checks` already uses). With no `GIT_INDEX_FILE` set (tests, direct calls), every read is what it was.

*Alternative: stop stripping `GIT_INDEX_FILE` in `_git_env`.* Rejected. It's stripped so that git calls into other
repositories, such as the tests' temporary ones, don't write into the hook's index. Putting it back by name, only for
reads of this repository's commit, keeps that.

### D2. The unstaged test compares the working tree with the commit's index

`git diff --name-only` against the committing index lists what the commit leaves out. With `-a` that's nothing, so the
check runs on what's committed. With `git commit <path>` it's every other edited tracked file, including ones staged
in `.git/index`. That's still a refusal, because the check runs on the working tree, which then isn't what's
committed. Today's fix text ("stage them") doesn't help a path commit, so the fix gains: "or, with
`git commit <path>`, name them too or commit without paths". The scenario "Unstaged changes still refuse a skippable
commit" is unchanged for a plain commit.

### D3. An unknown `before` falls back to the merge-base, with a note

In `github_ci_inputs`, a push's `before` is kept only if `git cat-file -e <before>^{commit}` succeeds. Otherwise the
base is `git merge-base origin/main <head>`, the same as for a first push. The run prints
`guard: the push's previous tip <sha7> isn't in this clone (a force push?), so the range starts where the branch left main (<sha7>).`
on stdout, beside the other notes. The function's return shape doesn't change.

*Alternative: fix it in `commits_in_range` (fall back to the merge-base there).* Rejected. The pre-push hook shares
that function, and only CI knows that `origin/main` is the base to use. The comment's suggestion was the same.

### D4. Wording

Use the wording suggested in #103's comments, adjusted to the lines as they are now (`docs/development-workflow.md:327`,
`README.md:84-85`, `.github/workflows/schedules.yml:17-18`). The docs rows for `commit-checks`, `delivered-file` and
archived tasks say they judge what `git commit -a` and `git commit <path>` commit, as the `schema-commit-type` row
does. The CI prose at line 151 no longer implies that a force push loses the range.

## Risks / Trade-offs

- [A hook run where git sets `GIT_INDEX_FILE` in a form not seen yet (an absolute path, a worktree's index)] →
  Resolving against `root` leaves an absolute path unchanged. The hook tests cover all three forms git uses
  (relative, `index.lock`, `next-index-*.lock`), each made by real `git commit` runs with the hooks on, not only by
  setting the variable.
- [A merge-base range judges more than the force push changed] → It judges the whole branch, as a first push does,
  which is what the pull request's run will judge anyway. It can't pass something the merge gate would refuse.
- [`origin/main` missing in some clone] → `merge-base` fails, the base is `None`, and behaviour is as today. The note
  isn't printed then.

## Migration Plan

Merged here. Then the owner-approved apply delivers `scripts/guard.py` to troupe and website (`guard_targets`): one
in-place update in each, and nothing else. Rollback is a revert here and another delivery.
