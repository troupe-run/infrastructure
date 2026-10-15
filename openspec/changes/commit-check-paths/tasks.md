# Tasks

## 1. The declaration is read, validated and decided

- [x] 1.1 Write failing tests in a new `scripts/tests/test_guard_check_paths.py`, each named for what its body checks
      (design D1, D2, D4, D5).
      - **Accepted:** `check_paths(text)` accepts a file with only `version = 1`, one with only `[skip]`, one with
        only scopes, and one with both.
      - **Refused**, each with an error naming the problem:
        - text that isn't TOML, a missing or unknown `version`, an unknown top-level table or key;
        - a group without `paths`, or with `paths` that isn't a list of strings;
        - a scope name that's bad (`Docs`, `1x`, `a_b`, `""`) or reserved (`none`, `full`);
        - each bad entry: `docs/*.md`, `src/?.py`, `[ab]/**`, `**`, `/abs/**`, `a\\b`, `a//b`, `./a`, `a/../b`, `""`;
        - overlaps: `a/**` with `a/b/**`, `a/**` with `a/b.md`, and `x.md` with `x.md`, each across skip and a scope
          and across two scopes. The message names both entries and both groups.
      - **Allowed:** the same entry twice in one group.
      - **Decided:** `check_scope(paths, declaration)` gives:
        - full, for an empty list, for any path in no group, and for `scripts/check-paths.toml` even when a group
          covers it;
        - nothing, when every path is skipped;
        - the sorted scope names the paths touch, when every path is skipped or scoped.

        `dir/**` matches at any depth, but not `dir` itself or `dirx/a`. An exact entry matches only itself.
      - **Property test** (hypothesis, as in the existing tests): for generated declarations without overlaps and
        generated paths, the result is full exactly when some path is in no group (or the list is empty, or holds the
        declaration). Otherwise it's the set of scopes some path is in, or nothing when that set is empty.

      Verify the new tests fail with `uv run pytest scripts/tests/test_guard_check_paths.py`. (Done as written; 1.3
      then allows scopes to overlap one another and narrows scope names to `[a-z][a-z0-9_]*`, design D1, D2.)
- [x] 1.2 Add `CHECK_PATHS = "scripts/check-paths.toml"`, the frozen `CheckPaths` dataclass, the `Scope` result,
      `CheckPathsError`, `check_paths(text)` (using `tomllib`) and `check_scope(paths, declaration)` to
      `scripts/guard.py`, as pure functions beside the delivered-file rule (design D2, D4, D5). Verify 1.1's tests
      pass, and that `uv run scripts/check.py` passes (mypy --strict, ruff)

- [x] 1.3 Change 1.1's tests to the revised rules (design D1, D2, D4), and verify the changed ones fail:
      - scopes may overlap: `blah` (`path1/**`, `another/**`) and `blech` (`path1/**`) are accepted, and
        `check_scope(["path1/blah.py"])` gives `blah`, `blech`; `another/x` gives `blah` alone;
      - skip still may not overlap a scope (`a/**` with `a/b/**`, `a/**` with `a/b.md`, `x.md` with `x.md`), and the
        message names both entries and both groups;
      - scope names: `a_b` and `docs2` are accepted; `a-b`, `Docs`, `1x`, `_a`, `""`, `none` and `full` are refused;
      - the property test lets one top-level name belong to several scopes, and expects every scope a path is in.
- [x] 1.4 Make `check_paths` refuse only skip-with-scope overlaps, narrow `SCOPE_NAME` to `[a-z][a-z0-9_]*`, and make
      `check_scope` collect every scope a path's entries match rather than the first. Verify 1.3's tests pass, the
      rest of `scripts/tests/` passes, and `uv run scripts/check.py` passes

## 2. The pre-commit check runs what the staged paths need

- [x] 2.1 Write failing tests in `scripts/tests/test_guard_commit_rules.py`, using `make_repo` and a check script that
      appends its arguments to a marker file, so a test can tell whether it ran and with what (design D3, D4, D5, D8).
      Commit a declaration that skips `openspec/**` and has scopes `docs` (`docs/**`) and `api` (`api/**`). Then:
      - **Skipped:**
        - committing only an `openspec/` file is allowed, nothing is recorded, and stderr says
          `only openspec/** is staged; the check is skipped (scripts/check-paths.toml)`;
        - `git mv` of an active change into `openspec/changes/archive/` is skipped the same way.
      - **Scoped:**
        - a `docs/` file, alone or with an `openspec/` file, records `--scope docs`, and stderr names the scope;
        - a `docs/` file plus an `api/` file records `--scope api --scope docs`;
        - a scoped run whose check fails is refused, naming the gate.
      - **Full check:**
        - an `openspec/` file plus `README.md` records no arguments;
        - `git mv src.py openspec/src.py` runs the full check;
        - staging `scripts/check-paths.toml` runs the full check, even when it now skips `scripts/**`;
        - `--allow-empty` runs the full check.
      - **Unchanged:** an unstaged change to a tracked file still refuses with the unstaged-changes message, and
        nothing is recorded.
      - **No declaration:** an `openspec/`-only commit runs the full check.
      - **Malformed declaration committed:** the commit is refused under `commit-checks`, the message names
        `scripts/check-paths.toml`, the problem and the fix, and nothing is recorded.

      Verify they fail
- [x] 2.2 In `commit_checks`, after the unstaged-changes refusal, list the staged paths with
      `git diff --cached --name-only --no-renames`, read the staged declaration with `ReadStaged`, decide with
      `check_scope`, and then do one of three things. Skip with the announcement. Run `check.py` with one `--scope`
      per scope, announced and streamed and with the same timeout and failure handling. Or run the full check as today.
      A malformed declaration refuses as D5 says. Verify 2.1's tests pass, the existing `commit_checks` tests pass
      unchanged, and `uv run scripts/check.py` passes
- [x] 2.3 Add a test in `scripts/tests/test_guard_commit_rules.py`: with scopes `blah` (`path1/**`, `another/**`) and
      `blech` (`path1/**`) declared, committing `path1/blah.py` records `--scope blah --scope blech`. Verify it passes
      after 1.4 (no change to `commit_checks` is expected; if one is needed, it's made here)
- [x] 2.4 Update `docs/development-workflow.md`:
      - the `commit-checks` row: add "or while `scripts/check-paths.toml` is malformed", and say a commit runs only
        what its staged paths need;
      - the paragraph after the rules table: rewrite it to cover the declaration's format (skip and scopes, the two
        kinds of entry, overlapping scopes allowed but not skip with a scope, scope names and reserved names), the
        decision table, what always runs the full check, and that the file is each repository's own and isn't
        delivered;
      - replace "10–15 seconds" there with a current measured time for this repository.

      Verify `uv run pytest scripts/tests/test_guard_docs.py` and `uv run scripts/check.py` pass

## 3. CI reads the same declaration

- [x] 3.1 Write failing tests for `guard.py check-scope` (design D6), run as a subprocess in a `make_repo` repository
      holding 2.1's declaration plus the overlapping `blah`/`blech` scopes from 2.3, with the paths on stdin:
      - `openspec/a.md` alone prints `scope=none` and `check-args=`, and exits 0;
      - `docs/a.md` plus `openspec/a.md` prints `scope=docs` and `check-args=--scope docs`;
      - `docs/a.md` plus `api/b.py` prints `scope=api,docs` and `check-args=--scope api --scope docs`;
      - `path1/blah.py` prints `scope=blah,blech`;
      - `README.md` with anything prints `scope=full` and `check-args=`;
      - empty stdin prints `scope=full`, and so does no declaration;
      - a malformed declaration exits 1, prints the commit hook's refusal text to stderr, and prints nothing to stdout.

      Verify they fail
- [x] 3.2 Add the `check-scope` subcommand to `main`, reading `CHECK_PATHS` from the working tree, and list it in the
      module docstring's entry points. Verify 3.1's tests pass and `uv run scripts/check.py` passes
- [x] 3.3 Document `check-scope` in `docs/development-workflow.md`. Cover the `git diff ... | uv run --no-project
      scripts/guard.py check-scope` line, its outputs, how a job uses `scope` and `check-args`, and what CI still
      decides itself (the base, and passing an empty list when it can't). Verify `uv run scripts/check.py` passes

## 4. Scopes are test tags, and every test run checks them

- [x] 4.1 Write failing tests in `scripts/tests/test_guard_check_paths.py` for the pure functions (design D8, D9):
      - `marker_expression(("api", "docs"))` is `"api or docs"`, and one name is just the name;
      - `tag_violations(TestReads(...), declaration)`, with skip `openspec/**`, scopes `docs` (`docs/**`), `blah`
        (`path1/**`) and `blech` (`path1/**`):
        - a test reading `docs/runs.md` untagged gets one violation naming the test, the file and the tag `docs`;
        - a test tagged `blah` reading `path1/x.json` gets one naming `blech`;
        - a test reading `openspec/a.md` gets one naming the file and the skip entry `openspec/**`, whatever its tags;
        - a test reading only `README.md`, or `docs/runs.md` while tagged `docs`, gets none.

      Verify they fail
- [x] 4.2 Add `TestReads`, `tag_violations` and `marker_expression` to `scripts/guard.py` as pure functions beside
      `check_scope`. Verify 4.1's tests pass and `uv run scripts/check.py` passes
- [x] 4.3 Write failing tests in a new `scripts/tests/test_guard_pytest.py` that run pytest in a subprocess on a
      throwaway project (`tmp_path`, with `scripts/guard.py`, `scripts/guard_pytest.py`, a `conftest.py` holding
      `pytest_plugins = ["guard_pytest"]`, and a declaration with skip `openspec/**` and scope `docs`):
      - a test that reads `docs/a.md` through `Path.read_text` without a marker fails, and the output names the test,
        `docs/a.md` and `docs`; the same test marked `docs` passes;
      - a test that reads `openspec/a.md` through `open` fails, naming the skip entry;
      - a test that reads a file it wrote under its own `tmp_path` passes;
      - `--strict-markers` accepts `@pytest.mark.docs`, which nothing else registered;
      - with no declaration, every test passes and nothing is registered;
      - with a malformed declaration, the session fails with D5's message.

      Verify they fail
- [x] 4.4 Add `scripts/guard_pytest.py` (design D9): the source note on its first line, as `guard.py` has; at session
      start, read the declaration from the root directory, register each scope as a marker, and install one audit
      hook; record files opened inside the repository during each test's setup, call and teardown; fail the test with
      every violation `tag_violations` finds. Add it to `guard_files` in `tofu/guard_delivery.tf`, and to the
      delivered list in `scripts/tests/test_guard_delivery.py` if that test enumerates them. Verify 4.3's tests pass,
      `tofu validate` passes, and `uv run scripts/check.py` passes
- [x] 4.5 Write failing tests in `scripts/tests/test_check.py` for this repository's `check.py --scope` (design D8):
      `--scope nope` exits non-zero before any gate runs, naming `nope` and `scripts/check-paths.toml`; the gate list
      for a declared scope `docs` (in a declaration passed to `gates()`) keeps every gate and gives pytest
      `-m docs`; with two scopes, `-m "api or docs"`; with none, pytest gets no `-m`. Then add `--scope`
      (`action="append"`) to `check.py`, reading the declaration through `guard.check_paths` and building the
      expression with `guard.marker_expression`. Verify the tests pass and `uv run scripts/check.py` passes
- [x] 4.6 Document scopes as tags in `docs/development-workflow.md`: the `--scope` contract every `check.py` takes on
      (every gate runs, the tests narrow, an undeclared scope is refused), the pytest convention (a marker per scope,
      `-m`), the tag check and the plugin, what the audit hook can't see (reads in subprocesses), and that another
      runner, such as vitest, follows the same contract with its own adapter. Add `scripts/guard_pytest.py` to the
      list of delivered files. Verify `uv run scripts/check.py` passes

## 5. This repository adopts it

- [x] 5.1 Confirm that no gate here reads `openspec/`: `git grep -n openspec -- 'scripts/tests/*.py'` shows only
      temporary trees, fake API paths and commit messages, and `scripts/check.py` runs no gate over it. Record the
      result in this task. Then add `scripts/check-paths.toml` with `version = 1` and `[skip] paths =
      ["openspec/**"]`. Its comment says what the file is, what reads it, that a path in no group runs the full check,
      and why `openspec/**` is safe. Load the plugin with `-p guard_pytest` in `pyproject.toml`'s pytest
      `addopts` (a `pytest_plugins` line only works in a root `conftest.py`, which this repository doesn't have). Verify `uv run scripts/check.py` passes with the tag check active, which
      shows no test here reads `openspec/`, and record the test time before and after loading the plugin. Commit, and
      verify that commit runs the full check (the declaration is staged)
      Done 2026-10-15. `git grep -n openspec -- 'scripts/tests/*.py'` hits only `make_repo` trees under `tmp_path`
      (`conftest.py` `Repo.change`), commit messages (`docs(openspec): ...`), declarations and staged paths in the
      new tests, `test_oob.py`'s fake API path, and `test_plan_needed.py`'s path strings; `scripts/check.py` names no
      `openspec` path. With the plugin loaded: 796 passed in 70.86s, against 70.09s before (796 passed). A
      temporary probe test reading `openspec/config.yaml` failed at teardown with `guard: ...::test_reads_spec reads
      openspec/config.yaml, but scripts/check-paths.toml skips \`openspec/**\` ...`, and was deleted
- [ ] 5.2 Make the next `openspec/`-only commit on this branch, such as ticking 5.1, and verify the guard announces
      the skip and the commit is made without the check running. Record the output in this task

## 6. Evidence

- [ ] 6.1 In a local scratch clone of troupe (under the scratchpad, nothing pushed), on a branch named for a scratch
      change created with `openspec new change`:
      - copy in this branch's `scripts/guard.py` and `scripts/guard_pytest.py`, and commit them with `--no-verify`,
        since this stands in for the delivery;
      - add a declaration that skips `openspec/**` and has a `docs` scope (`docs/**`,
        `plugins/runner-scripted/README.md`);
      - load the plugin with `-p guard_pytest` in troupe's pytest `addopts` (with `scripts` on its `pythonpath`), and
        give `check.py` `--scope` as in 4.5;
      - run the full check once with no markers, and record which tests the tag check fails. Expect the six doc tests
        and `test_scripted_schemas.py`. Then mark them `docs`, rerun, and verify the full check passes. Commit (a full
        check, since the declaration is staged).

      Then:
      - commit only an `openspec/` file: verify the skip is announced and the commit is made in seconds;
      - commit a `docs/` file: verify `--scope docs` runs every gate but only the marked tests, and time it;
      - commit a source file: verify the full check runs.

      Record the commands, timings and output here, including the full run's time with and without the plugin
- [ ] 6.2 Run `uv run scripts/tofu.py plan` after fast-forwarding onto `origin/main`, and verify it shows
      `scripts/guard.py` updated and `scripts/guard_pytest.py` created in troupe, and nothing else. Check that the
      delivered list (`.github/guard-delivery.json`) gains the new file. Keep it for the pull request
- [ ] 6.3 Run `openspec validate commit-check-paths --strict` and verify it passes

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #45`, the evidence from 5.2 and 6.1, and the plan from
  6.2. CI must be green on all three OSes before the delivery is planned.
- Comment on troupe-run/troupe#101 with what it can use:
  - the declaration, `scripts/check-paths.toml` (format in design D1 and D2), with the docs scope from 6.1 as a
    starting point;
  - scopes as markers, the `--scope` contract its `check.py` takes on, and `guard.marker_expression` (D8);
  - the tag check and loading `guard_pytest` (D9), with the list of tests 6.1 found needing `docs`;
  - `guard.py check-scope` and its outputs (D6);
  - that troupe's files land with #101's change (D7).

  That records that both issues use one declaration.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers `scripts/guard.py` and `scripts/guard_pytest.py` to troupe.
- After the apply, confirm troupe's delivered files match `main` here. Then comment on #45 with the pull request and
  the archived change, close it, and check its roadmap card says Done.
