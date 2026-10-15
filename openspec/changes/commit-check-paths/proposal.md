## Why

The commit guard runs the repository's whole `scripts/check.py` before every commit, whatever the commit stages
(#45). In troupe that's about 3.5 minutes on macOS, and the workflow makes many commits that change no code. On
troupe-run/troupe#99, the archive commit `606f03c` only moved a change folder under `openspec/`, and the guard still
ran 1669 tests in 214 s before allowing it. The proposal commit before it, four new files under `openspec/changes/`,
took about as long.

troupe-run/troupe#101 asks the same question of troupe's CI, and adds a second case: a `docs/**` change can't skip
the tests, because six tests check the docs against the code, but it needn't run the other 1600. Both issues need one
answer to "what does a change to these paths have to run?", and only the repository knows it. The guard is generic,
so the rule can't live in it. This change builds what both need. troupe#101 then only has to fill it in for troupe.

A hand-kept list of "the tests that read docs" would go stale without anyone noticing: a new docs test left off it
would be skipped by every docs-only change. So the tests carry their own tags, and every run checks the tags against
what each test actually reads.

## What Changes

- **A repository declares what its paths need**, in `scripts/check-paths.toml`, which it owns (it isn't delivered).
  The format is closed: `version = 1`, a `[skip]` table of paths no gate reads, and any number of
  `[scopes.<name>]` tables, each listing the paths whose tests are tagged `<name>`. Each entry is an exact path or a
  directory written `dir/**`. Scopes may overlap one another. A path both skipped and in a scope, any other entry, and
  a scope name outside `[a-z][a-z0-9_]*` or reserved (`none`, `full`) are malformed. A path in no group needs the full
  check, so a new folder runs everything until someone declares otherwise (design D1, D2).
- **A change's paths decide what runs** (design D4):
  - every path skipped: nothing runs;
  - every path skipped or in a scope: every scope those paths are in runs, as
    `scripts/check.py --scope <a> --scope <b>`;
  - any path in no group, no paths at all, or a change to the declaration itself: the full check runs.
- **A scope is a test tag** (design D8). Given scopes, a repository's `check.py` runs every gate as usual and narrows
  only the tests, to those tagged with any of the scopes. It refuses a scope the declaration doesn't list. For pytest
  the tag is a marker named for the scope, and the tests run with `pytest -m "a or b"`. The guard itself stays
  generic, and only passes names. A future vitest repository follows the same contract with its own tagging.
- **Every test run checks the tags** (design D9). A test that reads a file under a scope's paths without that scope's
  tag fails, and so does a test that reads a skipped path. The rule is a pure guard function over plain data (each
  test's id, tags and files read). pytest uses it through a delivered plugin, `scripts/guard_pytest.py`, which records
  each test's reads through Python's audit hook and registers each declared scope as a marker. A repository loads it
  from `conftest.py` with one line.
- **The pre-commit hook uses the decision.** The staged paths are listed with rename detection off, so a file moved
  out of a read path counts by both its old and its new name (design D3). Whatever runs is announced first, naming the
  paths and the file that decided, for example `guard: only openspec/** is staged; the check is skipped
  (scripts/check-paths.toml).` A scoped run streams its output and has the same timeout as the full check.
- **A malformed declaration refuses the commit** under `commit-checks`, naming the file, what's wrong and the fix. It
  isn't treated as absent (design D5).
- **The rest of the commit rules don't change.** The unstaged-changes refusal still comes first, and the branch
  match, Conventional Commits, archived tasks and delivered files apply as to any other commit.
- **CI reads the same declaration with the same function.** `guard.py check-scope` reads changed paths on stdin and
  prints `scope=none`, `scope=full` or `scope=<a>,<b>`, plus `check-args=` holding the arguments to pass to
  `check.py`, for `$GITHUB_OUTPUT`. It's shaped like `scripts/plan_needed.py`. No input means `full`, and a malformed
  declaration exits non-zero (design D6).
- **This repository adopts it all:** `[skip] paths = ["openspec/**"]`, `--scope` in its `check.py` (it has no scopes
  yet, so every name is refused), and the plugin in its `conftest.py`, which proves on every run that no test reads
  `openspec/`. troupe's declaration, its `check.py --scope`, its `docs` markers and its `conftest.py` line land through
  troupe#101's change (design D7). The troupe case is verified here first, on a local scratch clone of troupe.
- **Docs:** `docs/development-workflow.md` covers the declaration, scopes as tags, the tag check and `check-scope`.
  troupe-run/troupe#101 gets a comment naming all of it.
- **Delivered to troupe**, like any guard change: `scripts/guard.py` and the new `scripts/guard_pytest.py`, after CI is
  green on all three OSes and the owner approves the plan.

Not in this change: troupe's own files (troupe#101); a vitest adapter, which the first TypeScript repository's change
writes against D8 and D9; `scripts/plan_needed.py`, which answers a different question (what OpenTofu reads).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: "Checks pass before a commit" lets a repository declare which paths need no check and
  which need only named scopes of it. A commit runs the least the declaration allows and says what it ran, and a
  malformed declaration refuses the commit. New requirements: CI gets the same decision from the guard; a scope runs
  every gate but only the tests tagged with it; every test run fails a test whose reads its tags don't cover.

`guard-delivery` is unchanged: its requirements cover every delivered file, and don't list them. The new file is one
more entry in `tofu/guard_delivery.tf`.

## Impact

- `scripts/guard.py`: reading and validating `scripts/check-paths.toml` (`tomllib`, standard library); deciding a
  change's scope; running nothing, the scopes or the full check in `commit_checks`; the `check-scope` subcommand;
  the tag rule and the pytest `-m` expression, as pure functions.
- `scripts/guard_pytest.py`: new, the pytest adapter. Delivered.
- `tofu/guard_delivery.tf`: `scripts/guard_pytest.py` added to the delivered files.
- `scripts/check-paths.toml`: new, skipping `openspec/**` for this repository.
- `scripts/check.py`, `scripts/tests/conftest.py`: `--scope`, and loading the plugin.
- `scripts/tests/`: tests for the declaration, each outcome, the malformed refusal, renames, `check-scope`, the tag
  rule, the plugin and `check.py --scope`.
- `docs/development-workflow.md`, `openspec/specs/development-workflow/spec.md`.
- troupe-run/troupe receives `scripts/guard.py` (updated) and `scripts/guard_pytest.py` (new) by delivery. Until it
  holds a declaration and loads the plugin, its commits run the full check as today.
