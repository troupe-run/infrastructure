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

      Verify the new tests fail with `uv run pytest scripts/tests/test_guard_check_paths.py`
- [x] 1.2 Add `CHECK_PATHS = "scripts/check-paths.toml"`, the frozen `CheckPaths` dataclass, the `Scope` result,
      `CheckPathsError`, `check_paths(text)` (using `tomllib`) and `check_scope(paths, declaration)` to
      `scripts/guard.py`, as pure functions beside the delivered-file rule (design D2, D4, D5). Verify 1.1's tests
      pass, and that `uv run scripts/check.py` passes (mypy --strict, ruff)

## 2. The pre-commit check runs what the staged paths need

- [ ] 2.1 Write failing tests in `scripts/tests/test_guard_commit_rules.py`, using `make_repo` and a check script that
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
- [ ] 2.2 In `commit_checks`, after the unstaged-changes refusal, list the staged paths with
      `git diff --cached --name-only --no-renames`, read the staged declaration with `ReadStaged`, decide with
      `check_scope`, and then do one of three things. Skip with the announcement. Run `check.py` with one `--scope`
      per scope, announced and streamed and with the same timeout and failure handling. Or run the full check as today.
      A malformed declaration refuses as D5 says. Verify 2.1's tests pass, the existing `commit_checks` tests pass
      unchanged, and `uv run scripts/check.py` passes
- [ ] 2.3 Update `docs/development-workflow.md`:
      - the `commit-checks` row: add "or while `scripts/check-paths.toml` is malformed", and say a commit runs only
        what its staged paths need;
      - the paragraph after the rules table: rewrite it to cover the declaration's format (skip and scopes, the two
        kinds of entry, no overlaps, reserved names), the decision table, what always runs the full check, the
        `--scope` contract a repository's `check.py` takes on when it declares a scope, and that the file is each
        repository's own and isn't delivered;
      - replace "10–15 seconds" there with a current measured time for this repository.

      Verify `uv run pytest scripts/tests/test_guard_docs.py` and `uv run scripts/check.py` pass

## 3. CI reads the same declaration

- [ ] 3.1 Write failing tests for `guard.py check-scope` (design D6), run as a subprocess in a `make_repo` repository
      holding 2.1's declaration, with the paths on stdin:
      - `openspec/a.md` alone prints `scope=none` and `check-args=`, and exits 0;
      - `docs/a.md` plus `openspec/a.md` prints `scope=docs` and `check-args=--scope docs`;
      - `docs/a.md` plus `api/b.py` prints `scope=api,docs` and `check-args=--scope api --scope docs`;
      - `README.md` with anything prints `scope=full` and `check-args=`;
      - empty stdin prints `scope=full`, and so does no declaration;
      - a malformed declaration exits 1, prints the commit hook's refusal text to stderr, and prints nothing to stdout.

      Verify they fail
- [ ] 3.2 Add the `check-scope` subcommand to `main`, reading `CHECK_PATHS` from the working tree, and list it in the
      module docstring's entry points. Verify 3.1's tests pass and `uv run scripts/check.py` passes
- [ ] 3.3 Document `check-scope` in `docs/development-workflow.md`. Cover the `git diff ... | uv run --no-project
      scripts/guard.py check-scope` line, its outputs, how a job uses `scope` and `check-args`, and what CI still
      decides itself (the base, and passing an empty list when it can't). Verify `uv run scripts/check.py` passes

## 4. This repository skips `openspec/**`

- [ ] 4.1 Confirm that no gate here reads `openspec/`: `git grep -n openspec -- 'scripts/tests/*.py'` shows only
      temporary trees, fake API paths and commit messages, and `scripts/check.py` runs no gate over it. Record the
      result in this task. Then add `scripts/check-paths.toml` with `version = 1` and `[skip] paths =
      ["openspec/**"]`. Its comment says what the file is, what reads it, that a path in no group runs the full check,
      and why `openspec/**` is safe. Commit it on its own, and verify that commit runs the full check (the declaration
      is staged)
- [ ] 4.2 Make the next `openspec/`-only commit on this branch, such as ticking 4.1, and verify the guard announces
      the skip and the commit is made without the check running. Record the output in this task

## 5. Evidence

- [ ] 5.1 In a local scratch clone of troupe (under the scratchpad, nothing pushed), on a branch named for a scratch
      change created with `openspec new change`:
      - copy in this branch's `scripts/guard.py` and commit it with `--no-verify`, since this stands in for the
        delivery;
      - add a declaration that skips `openspec/**` and has a `docs` scope (`docs/**`,
        `plugins/runner-scripted/README.md`);
      - add a minimal `--scope docs` to its `check.py` that runs the six doc tests, as D7 describes, and commit both
        (a full check, since the declaration is staged).

      Then:
      - commit only an `openspec/` file: verify the skip is announced and the commit is made in seconds;
      - commit a `docs/` file: verify only `--scope docs` runs, and time it;
      - commit a source file: verify the full check runs.

      Record the commands, timings and output here
- [ ] 5.2 Run `uv run scripts/tofu.py plan` after fast-forwarding onto `origin/main`, and verify it shows only the
      delivered `scripts/guard.py` changing in troupe. Keep it for the pull request
- [ ] 5.3 Run `openspec validate commit-check-paths --strict` and verify it passes

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #45`, the evidence from 4.2 and 5.1, and the plan from
  5.2. CI must be green on all three OSes before the delivery is planned.
- Comment on troupe-run/troupe#101 with what it can use:
  - the declaration, `scripts/check-paths.toml` (format in design D1 and D2), with the docs scope from 5.1 as a
    starting point;
  - the `--scope` contract its `check.py` takes on (D8);
  - `guard.py check-scope` and its outputs (D6);
  - that troupe's file lands with #101's change (D7).

  That records that both issues use one declaration.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers `scripts/guard.py` to troupe.
- After the apply, confirm troupe's `scripts/guard.py` matches `main` here. Then comment on #45 with the pull request
  and the archived change, close it, and check its roadmap card says Done.
