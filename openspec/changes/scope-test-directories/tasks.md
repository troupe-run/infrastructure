# Tasks

## 1. Test dependency

- [x] 1.1 Add `pytest-xdist` to the `dev` group in `pyproject.toml` and lock it (`uv lock`), for the parallel tests
  in 3 only (design D7). Verify `uv run python -c "import xdist"` succeeds, `uv run pytest` still passes serially,
  and `uv run scripts/check.py` passes.

## 2. The declaration reads `tests`

- [x] 2.1 Before changing the parser, add a property test in `scripts/tests/test_guard_check_paths.py`: any
  declaration of `paths` alone (generated skip and scopes) reads back exactly as written, and this repository's
  declaration reads. Verify it passes on the current code, before 2.2. After 2.3, compare the new parser with the
  one before this change (`git show f8328f8:scripts/guard.py`) over the same generated declarations, once, and
  record the result here. A lasting test can't do that comparison: after the merge, `main` is the new parser.
  - 2026-10-18: both tests pass on `f8328f8`'s parser (`2 passed`). After 2.3, a scratchpad script ran both parsers
    over 5,000 hypothesis-generated declarations (versions 1, 2 and `"1"`; skip and scope tables with `paths` and an
    unknown `why`; good, wildcard, absolute, `..`, empty and `**` entries; bad and reserved scope names; non-list
    and empty values). Every one gave the same `skip` and `scopes`, or a refusal with the same problem up to its
    `;` (the scope's unknown-key hint now names `tests` too), and every accepted one had `tests == ()`.
- [x] 2.2 Write the parsing tests (spec: "A scope can tag whole test directories", malformed and no-`tests`
  scenarios): a scope with `tests` parses into `CheckPaths.tests` in file order, with `scopes` unchanged; repeated
  and cross-scope overlapping entries are accepted; refused, each naming the place (`scopes.<name>.tests[i]`) and
  the entry: `tests` not a list, `tests = []`, a non-string, an exact file, `**`, a wildcard, a backslash, an
  absolute path, a `.`/`..`/empty segment, and `tests` under `[skip]`. Verify they fail on the current code.
- [x] 2.3 Implement D1-D3 in `scripts/guard.py`: the `tests` key on scopes only, the directory-only entry rule built
  on `_check_paths_entry`, `CheckPaths.tests` with a `()` default, and `CHECK_PATHS_FIX` naming the new key. Verify
  2.1 and 2.2 pass, and `uv run mypy` and `uv run ruff check` are clean.
- [x] 2.4 Add `directory_tags` and `unmatched_tests` (design D4, D6) with tests on plain data: a file under an entry
  at any depth gets the scope, a sibling with a shared prefix (`tests/a/**` vs `tests/ab/x.py`) doesn't, two scopes
  listing one directory give both; an entry with no file under it is reported with its scope, and its message names
  `scripts/check-paths.toml`, the scope, the entry and the fix; an entry outside every root isn't reported, one
  inside the root or equal to a root is. Verify they pass, and fail when `_matches` is swapped for a plain
  `startswith` without the `/` boundary (then restore it).
  - 2026-10-18: 22 new tests, failing before and passing after (131 in the file). With `_matches` swapped for
    `path.startswith(entry[:-3])`, 3 failed (`tests/ab/test_z.py` and `tests/a` tagged `blah`; the unmatched list
    lost `tests/a/**`); restored, all pass. The results are a small `UnmatchedTests` record whose `message` and
    `place` the plugin uses.

## 3. The plugin applies it

- [x] 3.1 Extend `scripts/tests/test_guard_pytest.py`'s throwaway project so a test can declare `tests` and lay out
  several test directories, and its `run_pytest` takes extra arguments (`-m`, `-n 2`, paths). Write the tests (spec:
  both new requirements): `-m <scope>` selects exactly the tests under the scope's `tests` plus any test marked by
  hand, serially and with `-n 2`, comparing the sets of passed node ids; an untagged test under a `tests` directory
  that reads the scope's path passes the tag check; two scopes listing one directory both select it; an entry
  matching no test fails the full run and the `-m <scope>` run, serially and with `-n 2`, with exit 1, the message
  in the output and no `INTERNALERROR`; running one file outside the broken entry passes; `pytest --markers` lists the
  scope's `tests`. Verify they fail on the current plugin.
  - 2026-10-18: 15 new tests (18 cases with the testpaths pair added in 3.2), 13 failing on the old plugin. The
    three that passed must pass either way: a read outside the scope's directories still fails, and runs of
    `suites/b` and `suites/b/test_b.py` pass.
- [x] 3.2 Implement D5 in `scripts/guard_pytest.py`: the `tryfirst` `pytest_collection_modifyitems` adding markers
  from `directory_tags`, the run's roots from `config.args` (D6), and the failing item for each unmatched entry,
  placed first and marked with its scope; the marker description lists `tests`; the module docstring says what the
  hook does. Verify 3.1 passes, every existing test in the file still passes, and `uv run scripts/check.py` passes.
  - 2026-10-18: 28 pass in the file. A test for a run from `testpaths` (`["suites"]` checks the missing entry,
    `["suites/b"]` doesn't) was added, as design D6's risks promised. `_record` now uses the same `_relative` helper,
    so the repository-relative rule is written once. With `trylast` in place of `tryfirst`, the four selection cases
    (both scopes, serial and `-n 2`) fail: `-m` has already deselected, so the scope's other directories look
    empty. Restored. The full check passes (1012 tests).
- [x] 3.3 Measure the hook's cost on this repository's own run: `uv run pytest -q` three times before and after 3.2
  (no `tests` keys here, so the hook only walks the items). Record the times here; verify the difference is within
  run-to-run noise.

  - 2026-10-18: the totals before and after can't be compared, because 3.1's tests start pytest subprocesses (and
    the machine was loaded: 81-131 s). So the same 952 tests (the new ones deselected with `-k`) ran with the old
    plugin (`904d7a9`) and the new one, alternating: old 96.2, 86.3, 96.2 s; new 84.3, 95.7, 91.6 s. No difference
    beyond noise. This repository declares no `tests`, so the hook returns at once.
## 4. Documentation

- [x] 4.1 In `docs/development-workflow.md`, describe the `tests` key: the example declaration gains a scope with
  `tests`, the entry rules say directories only, "A scope is a test tag" says a test under a scope's `tests` counts
  as tagged, and the unmatched-entry failure and narrower-run rule are stated, with the xdist behaviour. Update the
  top comment in `scripts/check-paths.toml` to mention the key. Verify `uv run scripts/check.py` passes (the docs
  tests read both) and the doc's example declaration parses with `guard.check_paths`.
  - 2026-10-18: the doc's example gains a `vcs_git` scope with `tests`; the entry rules, the directory tags, the
    unmatched-entry failure and the narrower-run rule are described. The example is now checked by a lasting test,
    `test_the_docs_example_declaration_is_one_the_guard_reads` in `test_guard_docs.py` (tagged `docs`), rather than
    once by hand.

## 5. Integration

- [ ] 5.1 In a scratch clone of troupe (not pushed, discarded afterwards), with `main` here's `scripts/guard.py` and
  `scripts/guard_pytest.py` copied in and one package scope given `tests` (e.g. `vcs_git` with its suite and the core
  suite): verify `uv run scripts/check.py --scope vcs_git` runs every gate and exactly the tests under those two
  directories (count from `pytest --collect-only -q -m vcs_git`), with and without `-n auto`; that renaming one entry
  to a missing directory fails both, naming the scope and entry; and that troupe's unchanged `check.py` and
  declaration otherwise behave as before (`--scope docs` selects the same count as on troupe's `main`). Record the
  counts and times here.
- [ ] 5.2 Run `uv run scripts/tofu.py plan` after fast-forwarding onto `origin/main`, and verify it shows
  `troupe:scripts/guard.py` and `troupe:scripts/guard_pytest.py` updated in place, and nothing else. Keep it for the
  pull request.
- [ ] 5.3 Run `openspec validate scope-test-directories --strict` and verify it passes.

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #86`, the evidence from 3.3 and 5.1, and the plan from
  5.2. CI must be green on all three OSes before the delivery is planned.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers `scripts/guard.py` and `scripts/guard_pytest.py` to troupe.
- After the apply, confirm troupe's delivered files match `main` here. Comment on troupe-run/troupe#109 that the key
  is delivered, with its final shape (design D1-D6), so `package-check-scopes` task 2.2 can check it against its D2.
- Comment on #86 with the pull request and the archived change, check it's closed, and check its roadmap card says
  Done.
