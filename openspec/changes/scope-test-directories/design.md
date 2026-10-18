## Context

See proposal.md for why. The current state:

- `guard.check_paths` (in `scripts/guard.py`) parses a closed schema. `[skip]` and each `[scopes.<name>]` hold only
  `paths`, and any other key is refused under `commit-checks` (design D5 of `commit-check-paths`). It returns
  `CheckPaths(skip, scopes)`, where `scopes` is a tuple of `(name, entries)` pairs.
- `CheckPaths.scopes` is read in four places: `check_scope` and `tag_violations` in `guard.py`, marker
  registration in `guard_pytest.py`, and each repository's own `check.py`
  (`{name for name, _ in declaration.scopes}`). troupe's `check.py` is troupe's file, not delivered, and does the
  same unpacking.
- `guard_pytest` registers each scope as a marker and checks each test's markers against its reads at teardown. It
  never adds a marker. pytest's `-m` deselects in its own `pytest_collection_modifyitems`, after collection.
- troupe's `parallel-tests` change runs the tests gate with `pytest -n auto` (pytest-xdist). Under xdist the
  controller collects nothing: each worker collects, runs `pytest_collection_modifyitems` (so `-m` deselects on the
  worker), and sends its item ids to the controller, which needs every worker's list to be the same.
- A spike on 2026-10-18 (pytest 9.1.1, pytest-xdist 3.8.0, in the scratchpad) showed:
  - a marker added in a `tryfirst` `pytest_collection_modifyitems` is selected by `-m`, serially and with `-n 2`;
  - raising `pytest.UsageError` or calling `pytest.exit` there gives a clean exit 4 serially, but under `-n 2` it's
    an `INTERNALERROR` (exit 3, 35 lines of xdist traceback), and the message is lost. Raising in
    `pytest_collection_finish` behaves the same;
  - adding a synthetic `pytest.Item` whose `runtest` fails gives exit 1 and prints the message in both modes. Marked
    with the scope, it survives `-m <scope>` in both.
- This repository's tests are all in `scripts/tests`, and its scopes are written as markers. It has no use for the
  key itself.

## Goals / Non-Goals

**Goals:**
- One place, the declaration, says which test directories a scope runs, and the guard applies it the same way
  serially and in parallel.
- Every existing declaration and every `check.py` keeps working, unchanged, after delivery.
- A `tests` entry that stops matching fails loudly, including in the scope's own run.

**Non-Goals:**
- Working out which suites reach a package. That's troupe's `package-check-scopes` (its design D3), which compares
  each scope's `tests` with the reach it computes.
- Excluding paths from a directory entry, or glob patterns. Entries stay the two forms D2 allows.
- A vitest adapter. The rule is in guard functions over plain data, as `tag_violations` is, so one can follow.
- Running this repository's own tests in parallel.

## Decisions

### D1. `tests` is an optional key on a scope, and the file stays `version = 1`

```toml
[scopes.vcs_git]
paths = ["packages/troupe-vcs-git/src/**", "packages/troupe-vcs-git/tests/**", "packages/troupe-vcs-git/README.md"]
tests = ["packages/troupe-vcs-git/tests/**", "packages/troupe/tests/**"]
```

A scope's table holds `paths` (required) and `tests` (optional). `[skip]` holds only `paths`: a skip has no tests to
run, so `tests` there is an unknown key. Other keys are still refused, and the error now says which keys the table
reads.

`version` stays 1. A version gate exists so an older reader refuses a file it would misread. The closed schema does
that already: a guard from before this change refuses `tests` as an unknown key, naming it, so it can't quietly ignore
the directories. Every existing file stays valid, so nothing has to be rewritten. `version = 2` would refuse just the
same in an old guard, but every repository would then have to edit its declaration to use one optional key. And the
order of work keeps an old guard from seeing the key anyway: the guard is delivered first (Migration Plan).

*Alternatives:* `version = 2` (above); a top-level `[tests]` table mapping scopes to directories, which splits one
scope across two tables; a single string rather than a list, which troupe's scopes can't use, since most run more than
one suite.

### D2. Entries are directories, with the `paths` rules, and the list isn't empty

Each entry passes `_check_paths_entry` (no wildcard but a trailing `/**`, no backslash, not absolute, no empty, `.`
or `..` segment, not `**` on its own) and must end in `/**`. An exact file is refused: tagging one file is what a
marker in that file is for, and allowing it would give two ways to do the same thing. `tests = []` is refused
too ("leave `tests` out instead"), for the same reason. An entry repeated in one list is allowed, as it is in `paths`.
Entries may overlap across scopes, and a test under both gets both tags.

A `tests` entry needn't be inside the scope's `paths`: troupe's `vcs_git` scope runs the core suite, which isn't
vcs-git's code. It isn't checked against `[skip]` either. A test file under a skipped path already fails the tag
check, because importing a module opens its file. Checked on 2026-10-18 with the current plugin: a test in
`openspec/tests/` fails, naming its own `.py` and `.pyc` under the `openspec/**` skip.

Each problem names the entry by its place (`scopes.vcs_git.tests[1]`) and the value, through `CheckPathsError`, so
the commit hook, `check-scope` and the plugin all print D5's message. `CHECK_PATHS_FIX` adds the key to the shape it
describes.

### D3. `CheckPaths` gains a `tests` field, and `scopes` keeps its shape

```python
@dataclass(frozen=True)
class CheckPaths:
    skip: tuple[str, ...]
    scopes: tuple[tuple[str, tuple[str, ...]], ...]
    tests: tuple[tuple[str, tuple[str, ...]], ...] = ()
    """Each scope that declares `tests`, with its entries, in file order."""
```

`scopes` stays `(name, paths)` pairs, so every `check.py` (troupe's included) and every caller in `guard.py` reads
it unchanged. The default keeps `CheckPaths(skip=..., scopes=...)` valid, which the existing tests construct.

*Alternative:* `scopes` as `(name, paths, tests)` triples, or a `Scope` record. Cleaner, but `name, _` unpacking in
troupe's `check.py` would raise on delivery, and troupe's file can change only through troupe's own pull request.

### D4. Two pure guard functions hold the rule; the plugin applies it

Beside `tag_violations`, so another runner's adapter can use the same rule (commit-check-paths D9):

- `directory_tags(path, declaration) -> frozenset[str]`: the scopes whose `tests` entries cover a test file, given
  as a repository-relative POSIX path. It uses the existing `_matches`.
- `unmatched_tests(test_files, roots, declaration) -> list[tuple[str, str]]`: each `(scope, entry)` that matches none
  of the collected test files, among entries inside the run's roots (D6), in declaration order. It also gives each
  entry's message, naming the file, the scope, the entry and the fix: correct the entry if the directory moved, or
  take it out.

### D5. The plugin adds markers in a `tryfirst` collection hook, and reports an unmatched entry as a failing test

`guard_pytest` gains a `pytest_collection_modifyitems` with `tryfirst=True`, so it runs before pytest's own hook
deselects by `-m` and `-k`. For each item, it takes the item's file (`item.path`), made relative to the repository
root as `_record` does (real paths, POSIX), and calls `item.add_marker(name)` for each of `directory_tags`. Items
whose file is outside the repository are left alone. A test's own markers stay, so the tags are the union.

`tag_violations` then sees the added markers through `item.iter_markers()`, as it sees written ones, so the read
check is unchanged. Each scope's marker description, registered in `pytest_configure`, also lists its `tests`, so
`pytest --markers` shows what a scope runs.

For each unmatched entry, the hook puts a failing item first in `items`: a small `pytest.Item` subclass with a node id
like `scripts/check-paths.toml::scopes.vcs_git.tests[1]`, the scope's marker, and a `runtest` that fails with D4's
message (shown without a traceback). It's marked with its scope, so `-m vcs_git` keeps it, and the scope's run fails
rather than finding nothing to run (exit 5), which `check.py` would read as a pass. A full run keeps it as well.

Under xdist, every worker collects the same files and so adds the same markers and the same failing items, in the same
order. The controller's check that workers agree then passes, and one worker runs and reports the failure.

*Alternatives,* all from the spike: `pytest.UsageError` or `pytest.exit` in the hook (clean serially, an
`INTERNALERROR` that hides the message under xdist); failing in `pytest_collection_finish` (the same); a check in the
xdist controller (it collects nothing, and the plugin would then depend on xdist). Adding markers in
`pytest_itemcollected` would work for selection, but the unmatched check needs the whole collection, so both are done
in one hook.

### D6. Every entry is checked, unless the run names the paths it collects

When pytest is given no path arguments (`config.args_source` is `TESTPATHS` or `INVOCATION_DIR`), every `tests`
entry is checked. That's every full run and every `check.py --scope` run. When it's given paths (`ARGS`), those are
the run's roots: each with any `::` part dropped, resolved against the invocation directory, made relative to the
repository root. An entry is then checked when a root is the repository root, contains the entry's directory, or is
that directory. So running one test file, or another package's suite, never fails for a scope it didn't collect from.

The first version took the roots from `config.args` in every case, which pytest fills from `testpaths` when no
paths are given. The troupe dry run (task 5.1) showed that misses the case this exists for. `testpaths` lists the
suites that exist, so a stale entry (`packages/troupe/testz/**`) was outside every root, and both the full run and
`--scope vcs_git` passed without the suite. A renamed directory is renamed in `testpaths` too, and the old entry is
then outside it in the same way.

An entry whose directory is collected but excluded by `--ignore` or `--ignore-glob` does fail, as its tests aren't
collected. That's the safe side: the full check and every scoped run pass no such options. The message's fix covers
it.

*Alternatives:* check every entry on every run (it breaks running one file while working, which nobody would
tolerate, so it would be turned off and catch nothing); take the roots from `testpaths` too (above).

### D7. pytest-xdist joins this repository's dev dependencies, for the tests only

The parallel case is part of what #86 asks to be proved. The guard's tests already run pytest in a subprocess on a
throwaway project (`test_guard_pytest.py`), so those tests run it a second time with `-n 2`. The test environment
needs `pytest-xdist` installed for that, so it joins the `dev` group in `pyproject.toml` and `uv.lock`. The guard
itself stays standard library only, and the plugin doesn't import xdist. The parallel tests don't skip when xdist is
missing: a skip would pass without proving anything, so a missing package fails them.

## Risks / Trade-offs

- [A broken scope fails only runs that include its failing item] → A run selecting a different scope (`-m docs`)
  drops it, so a `docs`-only commit doesn't notice a broken `vcs_git` entry. The scope's own run, every full run, and
  every push to `main` fail it, and the commit that renames the directory isn't scoped to `docs`.
- [The path arguments don't match a run's real roots in some invocation] → D6 then checks fewer entries or more.
  Fewer means a missed warning, which the next full run catches, since it names no paths. More means a failure
  naming the entry, whose fix is clear. The tests cover `testpaths`, no arguments, a directory holding the entry, one
  file, and another suite.
- [A test's `item.path` is the file that defined it, not where it was parametrised or collected] → For Python tests
  these are the same. A plugin item from a non-Python file uses that file, which is the right directory too.
- [Workers collect differently] → Every worker reads the same declaration and files, so their tags and failing
  items match. If they didn't, xdist would refuse the run, loudly, rather than run the wrong tests.
- [An older guard meets a declaration with `tests`] → It refuses the commit as malformed, naming `tests`, and points
  to `CHECK_PATHS_FIX` from before the change. Delivering first (below) avoids it.

## Migration Plan

1. Merge here. This repository's declaration doesn't change apart from its comment, so its behaviour doesn't either.
2. CI is green on all three OSes. The owner approves the `apply` job, which delivers `scripts/guard.py` and
   `scripts/guard_pytest.py` to troupe. troupe's declaration has no `tests` keys, so nothing changes there.
3. troupe's `package-check-scopes` adds its package scopes with `tests`, in one commit, which runs the full check.

Rollback: before troupe uses the key, revert here and deliver again. Once it does, take its `tests` keys out first
(troupe's own pull request), or the older guard refuses the declaration.
