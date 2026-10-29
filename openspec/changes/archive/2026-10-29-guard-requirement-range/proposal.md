# Proposal

Issue: #220. Found on troupe-run/troupe#181 (its issue is troupe-run/troupe#179).

## Why

When Dependabot moves a version **range** in a manifest, as for `uv-build`'s build-system requirement, its commit's
subject is `chore(deps-dev): Update uv-build requirement`, with no versions at all. The Dependabot exemption
(dependabot-exemption design D5) reads an update's kind only from a subject's "from A to B", so it calls the update
unreadable and refuses it under `commit-branch-change`. troupe #181 moves `>=0.13.0,<0.14` to `>=0.13.5,<0.14` in
nine `pyproject.toml` files: a patch move inside one minor series, which is what the light path is for. The exemption
listed requirement ranges as a non-goal "if they turn out to be frequent"; every range bound in troupe's manifests
(`eventsourcing>=9.5.6,<9.6`, `ruamel.yaml>=0.19.1,<0.20`, `uv_build>=0.13.0,<0.14`) will hit this the first time a
release leaves its range.

## What Changes

- **The guard reads a requirement update's versions from the manifest lines its commit changes**, not from its
  message. On a reserved `dependabot/` branch only Dependabot writes the diff, as it writes the message, so the diff
  is as trustworthy and, unlike the message, always says what moved. The pull request's title, which anyone with
  write access can edit, stays unread (dependabot-exemption design D3).
- **A requirement update counts as minor or patch** when every changed manifest line only moves version numbers, of
  the dependency the subject names, and every number that moves goes up by a minor or patch step under the same
  counting the version bumps use. `>=0.13.0,<0.14` to `>=0.13.5,<0.14` is a patch. A bound that moves a major step
  (`<1` to `<2`) is major, and a line that changes anything else, a bound that goes down, or a manifest the guard
  can't pair line for line is unreadable. Each is still refused, and the refusal says which.
- **The commit message's `updated-dependencies` metadata isn't used for the range**: on #181 it says
  `dependency-version: 0.13.3` while the diff writes `0.13.5`. An `update-type` line, where present, is still checked
  as today.
- **`dependabot/fetch-metadata` is not adopted** (the issue asked). For a subject without versions it reads the pull
  request's title, and it splits a range on dots as if it were one version (design D1).
- **`dependabot-issues` counts the same range the same way**, from the pull request's title, so a requirement update's
  issue says "patch" or "minor" and no longer says it needs an OpenSpec change when the guard will let it through. A
  differential test holds the two readings equal, as one does for version bumps.
- **`docs/development-workflow.md`'s Dependabot section** says requirement updates are read too, and which ones still
  take an OpenSpec change.
- **After delivery**, troupe #181 is rebased with `@dependabot rebase` and must pass `guard`; troupe #179's stale body
  gets a comment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: the minor-or-patch condition of the Dependabot exemption also reads a requirement-range
  update from its manifest lines; the scenario that refuses `Update uv-build requirement` changes.
- `dependency-updates`: the issue's update type for a requirement-range title is counted from its ranges, not
  reported as unknown.

## Impact

- `scripts/guard.py` (delivered to troupe and website): a requirement-subject pattern, the manifest-line reading, and
  the range counting beside `dependabot_update_kind`.
- `scripts/dependabot_issues.py`: the range counting for a title's ranges (not delivered; runs in infrastructure).
- `scripts/tests/test_guard_dependabot.py`, `scripts/tests/test_dependabot_issues.py`.
- `docs/development-workflow.md`.
- The plan changes the delivered `scripts/guard.py` in troupe and website, and nothing else.
