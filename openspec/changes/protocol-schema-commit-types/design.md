# Design

## Context

See proposal.md for why. What the guard does today, in `scripts/guard.py`:

- `commit_message` judges a message's first line alone. `run_commit_msg` (the `commit-msg` hook) calls only that.
- `run_pre_commit` sees the staged paths but not the message, because git runs `pre-commit` before the message exists.
- `run_pre_push` re-applies only the message rule, to each commit being pushed (`nonconforming_commits`).
- `run_ci` re-applies the message rule, the branch rule, the archive rule and the delivered-file rule to each commit in
  the range, listing each commit's paths with `git diff-tree --no-commit-id --name-only -r`.
- `_git_env` strips `GIT_INDEX_FILE` from every nested git call, so tests' temporary repositories don't inherit the
  hook's repository. During `git commit -a` or `git commit <path>`, git points `GIT_INDEX_FILE` at the index it is
  about to commit (`.git/index.lock`, or a temporary `next-index-*.lock`), which differs from `.git/index`.

What release-please releases (googleapis/release-please, `src/util/filter-commits.ts` and `src/commit.ts`, read on
2026-10-23): a commit counts towards a release when its type is in a visible changelog section, by default `feat`,
`fix`, `perf` and `revert`, or when it carries a `BREAKING CHANGE` note, which the parser adds for `!` in the header, a
`BREAKING CHANGE:` footer or `BREAKING-CHANGE:` in the body. troupe's `release-please-config.json` sets no
`changelog-sections`, so the defaults apply. Its `protocol` package is the `protocol/` directory, and troupe's
`scripts/package_schemas.py` fails a generated copy that differs from `protocol/schemas/`.

## Goals / Non-Goals

**Goals:**
- Refuse a schema change under a non-releasing type at every layer that already checks messages: commit, push and
  the `guard` check.
- Judge exactly the files the commit contains, however it was made.

**Non-Goals:**
- Checking that the release actually happened, or that `version.json` is right: troupe's check and release-please
  own that.
- Judging the generated copy under `packages/troupe/src/troupe/protocol/`: a change there without one at the source
  already fails troupe's check.
- Fixing how the pre-commit hook reads the index during `git commit -a` (see Risks). This change reads the right index
  for its own rule only.

## Decisions

### D1. The path is a constant in the guard, and the rule is inert without it

`SCHEMA_PATHS = ("protocol/schemas/",)` sits beside `RELEASE_REPOSITORIES` in `scripts/guard.py`, with a docstring
naming troupe#140 and this change. A commit is judged by whether any path it changes starts with one of them, so in a
repository without that directory the rule never fires. That works offline in the local hooks, which don't know the
repository's name.

*Alternative:* a declaration in troupe (a table in its `scripts/check-paths.toml`, or a new file) naming the paths
that must release. It keeps troupe's layout in troupe, but needs a second, troupe-side pull request before the rule
does anything, and its own malformed-input handling, for one path that has been stable since the protocol's first
schema. `RELEASE_REPOSITORIES` already names troupe in the guard, so this follows existing practice. If a second
repository ever needs the rule with different paths, a declaration is the time to move it.

### D2. What releases mirrors release-please's defaults, in one place

`RELEASING_TYPES = ("feat", "fix", "perf", "revert")` beside `COMMIT_TYPES`, with a docstring citing
`filter-commits.ts`. A commit is breaking when its header has `!` before the colon, or a line of its message starts
with `BREAKING CHANGE:` or `BREAKING-CHANGE:`. Anchoring the footer at the start of a line is stricter than
release-please's unanchored body match, so the guard can only refuse a commit that would have released, never let
through one that wouldn't.

*Alternative:* read `changelog-sections` from the repository's `release-please-config.json`. It would follow a config
change automatically, but adds a JSON reader and a malformed-config refusal to every commit in every governed
repository, for a setting troupe doesn't use. Rejected for now; a test pins the constant to the defaults it copies.

### D3. A new rule id, `schema-commit-type`, overridable

A separate id rather than a second meaning for `commit-message`: the refusal's problem and fix are different (the
message is well formed; its type is wrong for what it changes), and an owner's override for one must not excuse the
other. It goes in `OVERRIDABLE_RULES` like every git rule, so the owner can grant a one-off.

The problem names up to five schema files and the commit's type. The fix lists the releasing types, says a breaking
change of any type is allowed, and gives an example (`fix(protocol): <what changed>`). It also says the schema change
can go in its own commit when the rest of the work shouldn't release.

### D4. The commit-msg hook reads the index git is committing

`run_commit_msg` runs the new rule after `commit_message`, with the paths from `git diff --cached --name-only
--no-renames` run against the hook's own `GIT_INDEX_FILE` when git set one, resolved against the repository root.
Every other nested git call keeps stripping it. So `git commit -a` and `git commit <path>` are judged on what they
commit, and unstaged schema edits don't count. `--no-renames` lists both sides of a rename, so moving a schema out of
`protocol/schemas/` counts as a change to it.

The message rule runs first: a message that isn't a Conventional Commit has no type to judge, and gets the
`commit-message` refusal.

### D5. Push and CI judge each commit's own changes

A shared helper lists one commit's paths (`git diff-tree --no-commit-id --name-only --no-renames -r --root <sha>`;
`--root` so a repository's first commit lists its files) and judges its message. `run_pre_push` and `run_ci` each
add one decision over the range, naming each failing commit as `<sha7> '<first line>' (<schema files>)`, as
`nonconforming_commits` does. This is what catches a commit amended or reworded after the hook ran (D4 sees only the
index against `HEAD`, so `git commit --amend` without new staged changes judges nothing), and anything made with
`--no-verify`.

### D6. A fixup is judged by the commit it names

As `commit_message` does, `fixup! `, `squash! ` and `amend! ` prefixes are stripped and the named subject's type is
judged, since the fixup will be folded into that commit. A `fixup! docs: x` that changes a schema is refused.

## Risks / Trade-offs

- [troupe sets `changelog-sections` one day, and the guard's list goes stale] → The constant's docstring and the
  rules doc say where it comes from; a change to troupe's release config is reviewed here when it touches releasing.
- [A commit made with `--amend` isn't judged until the push] → The pre-push hook and the `guard` check judge it, so it
  can't merge; the refusal names how to reword it.
- [The pre-commit hook's own reads use `.git/index`, not `GIT_INDEX_FILE`, during `git commit -a`] → Pre-existing and
  outside this rule. Task 1.4 records what it does, so a follow-up can be raised on infrastructure#103 if it's wrong.
- [The rule is troupe-specific code in a shared guard] → It is one constant, inert elsewhere, with D1's move to a
  declaration available if that ever changes.

## Migration Plan

Merged here, then delivered to troupe and website by the usual apply after the owner approves the plan. Nothing in
troupe's history is judged retroactively: only commits pushed after delivery are checked. Rollback is a revert here
and a new delivery.
