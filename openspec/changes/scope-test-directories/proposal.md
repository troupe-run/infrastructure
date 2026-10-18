## Why

A scope in `scripts/check-paths.toml` selects tests by tag (design D8 of `commit-check-paths`), and pytest's only tags
are markers written in the test source. troupe's package scopes (troupe-run/troupe#109, its `package-check-scopes`
change) select whole suites: a change to `packages/troupe-vcs-git/` must run the vcs-git suite and every suite that
reaches it. Tagging each of about 90 modules with `pytestmark` is a hand-kept list, and the declaration's schema is
closed, so a scope can't name the test directories it runs. The owner chose a `tests` key on the scope, applied by
the delivered `guard_pytest` plugin, over a troupe-local conftest hook (2026-10-18, #86), so the declaration stays the
one place that says which suites a scope runs.

## What Changes

- `guard.check_paths` accepts an optional `tests` key on `[scopes.<name>]`: a non-empty list of `dir/**` entries,
  with the same entry rules as `paths` but directories only. The schema stays closed. `[skip]` still holds only
  `paths`, every other key is still refused, and the file stays `version = 1`, since every existing declaration is
  still valid and an older guard refuses the new key by name.
- The parsed declaration keeps `scopes` exactly as it is, and gains a separate `tests` field. troupe's own `check.py`
  unpacks `scopes` as `(name, entries)` pairs, so changing that shape would break it on delivery.
- `guard_pytest` adds a scope's marker to every collected test whose file is under one of that scope's `tests`
  entries, before `-m` deselects anything. So `check.py --scope <name>` selects them, serially and under
  pytest-xdist, with no change to any `check.py`.
- A `tests` entry that matches no collected test fails the run with a test that names the scope, the entry and the
  fix, and carries the scope's marker so the scope's own run fails too. A renamed directory can't quietly stop a
  suite running. The check is skipped only for an entry outside what the run was asked to collect, such as when
  running one file.
- `guard.tag_violations` doesn't change: a tag from a directory counts like any other.
- The workflow doc describes the key. This repository's declaration doesn't use it: all its tests are in one
  directory, and its scopes stay markers.
- `pytest-xdist` joins this repository's dev dependencies, so the guard's tests can prove the key under `-n`.
- `scripts/guard.py` and `scripts/guard_pytest.py` are delivered to troupe and website.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: a scope can name the test directories it runs, the run fails when one of them matches no
  test, and a malformed `tests` entry is a malformed declaration.

## Impact

- `scripts/guard.py`: the declaration's parser, the `CheckPaths` record, and pure functions saying which scopes'
  `tests` cover a test file and which entries match nothing.
- `scripts/guard_pytest.py`: one collection hook, and the failing item for an unmatched entry.
- `scripts/tests/test_guard_check_paths.py`, `scripts/tests/test_guard_pytest.py`: parsing, selection (serial and
  `-n 2`), and the unmatched-entry failure.
- `pyproject.toml`, `uv.lock`: `pytest-xdist` in the dev group.
- `docs/development-workflow.md`, the comment at the top of `scripts/check-paths.toml`.
- troupe and website: the two delivered files change by delivery. Nothing there uses the key until troupe's
  `package-check-scopes` change adds `tests` to its scopes. website's declaration has only `[skip]`, and it runs no
  pytest.
