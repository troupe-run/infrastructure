# Design

## Context

See proposal.md for why. Current state, read on 2026-11-13 at infrastructure `d6fc32d`:

- **The exemption's kind reading** is `dependabot_ineligibility` in `scripts/guard.py`. A subject matching
  `DEPENDABOT_REQUIREMENT` is read from its manifest lines (guard-requirement-range D3). Any other subject is counted
  by `dependabot_subject_kind`, which needs `DEPENDABOT_SUBJECT`'s `from A to B`; without it the kind is "unknown"
  and the commit is refused. Every `update-type:` line must be minor or patch. Paths are judged separately by
  `non_dependency_paths`.
- **#285, as Dependabot wrote it** (commit `b25fc2f`, parent `0b0f7d9`, branch
  `dependabot/uv/types-pyyaml-6.0.12.20261030`):

  | Where | What it says |
  |---|---|
  | Commit subject | `chore(deps-dev): Bump types-pyyaml` |
  | Message, first body line | `Bumps [types-pyyaml](https://github.com/python/typeshed) from 6.0.12.20260906 to 6.0.12.20261030.` |
  | Message metadata | `dependency-name: types-pyyaml`, `dependency-version: 6.0.12.20261030`, `update-type: version-update:semver-patch` |
  | `pyproject.toml` | `"types-pyyaml>=6.0.12.20260906",` to `"types-pyyaml>=6.0.12.20261030",` |
  | `uv.lock` | the `types-pyyaml` package's `version` `6.0.12.20260906` to `6.0.12.20261030`, its `specifier`, sdist and wheel lines |
  | Pull request title | `chore(deps-dev): Bump types-pyyaml from 6.0.12.20260906 to 6.0.12.20261030` |

  Its refusal: `b25fc2f's subject 'chore(deps-dev): Bump types-pyyaml' doesn't give one dependency's versions, so
  its kind of update can't be read.`
- **#221 decided** not to trust the `updated-dependencies` metadata alone: on troupe #181 its `dependency-version`
  was stale after Dependabot updated the pull request in place. It also gives only the new version.
- **`dependabot_issues.read_update`** reads the pull request's title, which kept both versions for #285, so #288
  already says "patch". The guard never reads the title (dependabot-exemption D3: anyone with write access can edit
  it).

## Goals / Non-Goals

**Goals:**
- #285 passes `guard` after `@dependabot rebase`, with nothing else done to it.
- A shortened subject passes only when two independent readings of its versions agree, and a major one is still
  refused; every refusal says what was read and what failed.
- No subject that's read today is read differently.

**Non-Goals:**
- Changing `dependabot-issues`. It reads titles, which aren't shortened in any pull request seen so far. If one is,
  its issue says "unknown" and needs an OpenSpec change, which is safe; that would be a new issue.
- A shortened subject for a github-actions update. Actions' versions are short, so it hasn't happened; such a commit
  has no lock file or manifest reading, so it gets at most one reading and is refused.
- Trusting the `updated-dependencies` metadata as a reading.

## Decisions

### D1. Which commits take the new reading

A copied-shape pattern, `DEPENDABOT_SHORT_SUBJECT`, matches `<prefix>[Bb]ump <dependency>` with an optional
`in <directory>`, where the dependency is one run of non-space characters. A commit is read by it only when its subject
matches neither `DEPENDABOT_REQUIREMENT` nor `DEPENDABOT_SUBJECT`, which are tried first, as today. So a subject that
gives its versions keeps today's reading and outcome whatever its body and diff say, and a subject that is neither
(`Bump x from 1.0rc1 to 1.0`, which `DEPENDABOT_SUBJECT` matches, still counts as unknown) keeps its refusal.

### D2. Three readings

For a short-subject commit naming dependency X (compared under PEP 503's normal form, as requirement lines are):

1. **The message's `Bumps` line.** The message's first line after the subject's blank line must be
   `Bumps [X](<url>) from A to B.` (or `Bumps X from A to B.`), as Dependabot writes it. Only that line is read, so a
   changelog quoted further down can't be taken for it. On a reserved branch only Dependabot writes the message
   (dependabot-exemption D3), as for the subject. Gives versions A to B.
2. **Lock files.** For each `uv.lock` and `package-lock.json` the commit changes, the file is parsed at the commit's
   parent and at the commit (`tomllib`, `json`; both standard library). X's versions are collected from each: in
   `uv.lock`, every `[[package]]` whose `name` is X; in `package-lock.json`, every `packages` key whose last
   `node_modules/` segment is X. Exactly one distinct version must disappear and one appear (entries compared as multisets, so copies of
   one version moving together, hoisted and nested, are one move), giving A to B.
   Anything else in a changed lock file (unparseable, no `packages`, X not moving, several versions moving) is
   unreadable and refuses the commit, naming the file. Each lock file is its own reading of the versions, and they
   must agree with each other.
3. **Manifest lines.** For each `pyproject.toml` and `package.json` the commit changes, its lines are read as a
   requirement update's are (guard-requirement-range D3 steps 2 to 5: paired line for line, only version numbers
   differ, the removed line names X, every number goes up). Gives a kind (the largest step), not two versions,
   because a manifest holds a bound, which needn't be the locked version. A changed manifest line that can't be read
   refuses the commit, naming the line.

### D3. Agreement

- **At least two readings** must be present. A missing `Bumps` line or no changed lock file or manifest is simply
  absent; fewer than two present refuses the commit, saying which were found.
- **Versions agree exactly**: the `Bumps` line and every lock file must give the same A and B (a leading `v` is
  dropped). If they differ, the commit is refused naming each reading's versions.
- **A and B are counted** with `dependabot_update_kind`, the same counting as every bump and the issue, and B must be
  later than A (`_dependabot_raised`). Versions that aren't dotted digits, or that go down, are unreadable.
- **The manifest's kind agrees**: where manifest lines are read, their kind must equal A to B's. If it differs, the
  commit is refused naming both kinds.
- **The kind is the update's**: major is refused as for any bump; minor and patch are exempt. `update-type:` lines are
  checked as today, for every commit.

So at least two sources that only Dependabot writes on a reserved branch say the same thing, and the metadata is never
needed. For #285: the `Bumps` line and `uv.lock` both give `6.0.12.20260906` to `6.0.12.20261030`, and
`pyproject.toml` moves by a patch, so three readings agree.

### D4. How four-part versions compare

As every version here: a dotted run of digits, optionally after `v`, compared part by part as integers, with missing
parts counted as zero. The first part that differs decides: the first is major, the second minor, any later one patch.
So `6.0.12.20260906` to `6.0.12.20261030` is a patch (the fourth part, a date, moved), `6.0.12.x` to `6.0.13.x` is a
patch, `6.0.12.x` to `6.1.0.x` minor, and `6.0` to `6.0.0.1` a patch. This is the existing `dependabot_update_kind`,
unchanged, and it matches Dependabot's own `update-type` for #285. A version with a suffix (`1.0.0rc1`, `1.0.post1`)
isn't dotted digits, and is unreadable, as today.

### D5. Refusals

They join `dependabot_ineligibility`'s reasons under `commit-branch-change`, with the existing fix:

- `<sha>'s subject '<subject>' gives no versions, and its message and diff give <n> reading(s) of <X>'s, where two
  must agree: <what was found>`;
- `<sha>'s readings of <X>'s versions disagree: <reading> says A to B, <reading> says C to D`;
- `<sha>'s <path> can't be read for <X>: <why>` (a lock file) or the requirement line reasons for a manifest;
- `<sha>'s manifest lines move <X> by a <kind> step, but its versions A to B are a <kind>`;
- `<sha> ('<subject>', <X> A to B) is a major update`.

### D6. Tests, and the old path

- **#285 itself**: a fixture holds `pyproject.toml` and `uv.lock` from `0b0f7d9` and `b25fc2f` as a `git
  format-patch`. The test commits the files, applies the patch with `git am` on #285's branch (keeping Dependabot's
  message, author and diff), and runs `run_ci` for `troupe-run/infrastructure`. Written first, it fails on today's
  guard with #301's reason; it passes after D1 to D3.
- **The old path**: the existing tests pin every real bump's outcome (guard-requirement-range task 1.1), and a
  property test asserts that for any subject `DEPENDABOT_SUBJECT` or `DEPENDABOT_REQUIREMENT` matches, the short
  reading isn't taken. A one-off differential run loads `origin/main`'s `guard.py` beside the branch's and compares
  `dependabot_ineligibility` over generated commits (full, requirement, garbage and short subjects); every
  disagreement must be a short subject. Its result is recorded in tasks.md.
- **The issue's reading**: #285's real title read by `dependabot_issues.read_update` and its commit read by the guard
  both give patch.

## Risks / Trade-offs

- **[Risk] Lock formats change.** A new `uv.lock` or `package-lock.json` layout could hide X. → The reading refuses
  (red, not wrongly green), naming the file.
- **[Trade-off] Lock files are parsed whole.** `package-lock.json` can be a few MB; it's parsed twice per short
  commit, which is rare. Full-subject commits don't parse them.
- **[Trade-off] An indirect dependency's lockfile-only bump with no `Bumps` line** has one reading and is refused.
  Dependabot always writes the line, so this would be a change in its format, and the refusal says so.
- **[Risk] The copies drift.** Nothing here is copied from `dependabot_issues.py`; the counting is the existing shared
  `dependabot_update_kind`, still held equal to `update_type` by the existing tests.
