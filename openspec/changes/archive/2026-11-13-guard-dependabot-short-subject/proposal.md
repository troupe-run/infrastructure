# Proposal

Issue: #301. Found on this repository's #285 (its issue is #288).

## Why

When an update's versions are long, Dependabot shortens its commit's subject to `Bump <dependency>` and leaves out
"from A to B". #285 bumps `types-pyyaml` from `6.0.12.20260906` to `6.0.12.20261030`, a patch, changing only
`pyproject.toml` and `uv.lock`, and its commit `b25fc2f` says only `chore(deps-dev): Bump types-pyyaml`. The
Dependabot exemption reads a bump's kind only from its subject, so it calls the update unreadable and refuses it under
`commit-branch-change`. #285 has waited since 2026-11-09. Every calendar-versioned dependency (typeshed's `types-*`
stubs, for one) will do the same each time it's bumped.

## What Changes

- **A Dependabot commit whose subject is `Bump <dependency>` with no versions is read from its message and its
  diff.** Three readings are taken where they exist: the message's `Bumps [<dependency>](…) from A to B.` line, the
  dependency's version in each lock file the commit changes (`uv.lock`, `package-lock.json`, parsed before and after),
  and the dependency's lines in each manifest it changes (`pyproject.toml`, `package.json`, read as a requirement
  update's lines are). At least two SHALL be read, and they SHALL agree: the message's line and the lock files give
  the same two versions, and the manifest lines move by the same kind of step. Otherwise the commit is refused, and
  the refusal says which readings were missing or which disagreed.
- **The `updated-dependencies` metadata still isn't trusted alone** (#221). Its `update-type`, where present, is still
  checked against the kind, as today.
- **A subject that already gives its versions is read exactly as today.** The new reading applies only to a subject
  that matches neither the full bump pattern nor the requirement pattern; a differential test holds the old outcome
  for every subject that matches them.
- **Four-part versions are documented.** `6.0.12.20260906` to `6.0.12.20261030` is a patch: versions are compared as
  dotted runs of digits, missing parts counted as zero, and the first differing part decides: the first is major, the
  second minor, any later one patch. That's what Dependabot's own `update-type` says for #285.
- **`dependabot-issues` doesn't change.** It reads the pull request's title, which for #285 keeps both versions
  (`… from 6.0.12.20260906 to 6.0.12.20261030`), and its issue #288 already says patch. A test holds #285's title and
  commit to the same kind in both readers.
- **`docs/development-workflow.md`'s Dependabot section** says a shortened subject is read from its message and diff,
  and when it still takes an OpenSpec change.
- **After delivery**, #285 is rebased with `@dependabot rebase` and must pass `guard`; it then merges and closes #288.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: the Dependabot exemption's minor-or-patch condition also reads a bump whose subject leaves
  out its versions, from its message and its diff, with two readings agreeing.

## Impact

- `scripts/guard.py` (delivered to troupe and website): a short-subject pattern, the message's `Bumps` line, the lock
  file reading, and the agreement check beside `dependabot_ineligibility`.
- `scripts/tests/test_guard_dependabot.py`, and a fixture of #285's real files and commit.
- `docs/development-workflow.md`.
- The plan changes the delivered `scripts/guard.py` in troupe and website, and nothing else.
