# Tasks

## 1. Prove GitHub's behaviour first

- [x] 1.1 On a throwaway repository `troupe-run/infra-probe-skipped-matrix` (created from a public template-free
  repo, deleted afterwards), push a workflow with a `changes` job, a matrix job skipped by a job-level `if`, and a
  `guard tests` result job with `if: always()`; open one pull request that skips the matrix and one that runs it.
  Verify with `gh api repos/.../commits/<sha>/check-runs`: the skipped matrix reports one check run under its
  unexpanded name (design D6), and the result job reports `guard tests` as success on the first and on the second.
  Add a ruleset requiring `guard tests` and verify `gh pr merge --rebase` is accepted on the skipping pull request.
  Record the run URLs and outputs here, then delete the repository and verify `gh repo view` returns not found. If
  the naming differs from D6, stop and revise the design before going on.
  - Done 2026-10-17 on `troupe-run/infra-probe-skipped-matrix` (2 OSes × 2 Pythons, ruleset requiring `guard tests`
    from GitHub Actions). PR 1 (README only, run 39033316264): check runs `guard tests (${{ matrix.os }}, Python ${{
    matrix.python }}) | skipped`, `guard tests | success`, `changes | success`; merge state `CLEAN`, and `gh pr merge
    --rebase` merged it. PR 2 (`guard/` changed, run 39033322541): the four legs under their expanded names and
    `guard tests`, all success. With one leg failing: `guard tests | failure`, merge state `BLOCKED`. On the push to
    `main` (run 39033281766), `changes` was skipped, every leg ran and `guard tests` passed. D6 holds. The
    repository was deleted; `gh repo view` answers "Could not resolve to a Repository".

## 2. Scopes and tags

- [x] 2.1 Declare `dns`, `milestones`, `labels`, `tofu` and `docs` in `scripts/check-paths.toml` (design D1, D2),
  with the file's comment saying why `tofu` lists files by name, why `scripts/` has no scope (D3), and that tags are
  enforced for in-process reads only. Verify `uv run scripts/guard.py check-scope <<< tofu/dns.json` prints
  `scope=dns` and `check-args=--scope dns`, and that `scripts/tofu.py` prints `scope=full`.
- [x] 2.2 Tag the tests that read each scope's files (`pytestmark` where a module reads at collection or in a shared
  fixture, the test itself otherwise), starting from design's table and finishing from `guard_pytest`'s failures.
  Verify `uv run pytest` passes with no tag violation, and that removing the `dns` marker from `test_dns.py` makes it
  fail naming `tofu/dns.json` and the tag (then restore it).
- [x] 2.3 Verify each scope runs its tests: `uv run scripts/check.py --scope <name>` for each of the five passes, runs
  every non-test gate, and selects only tagged tests (`pytest --collect-only -q -m <name>` count recorded here, with
  the elapsed time of each scoped run against the full run's).
  - 2026-10-17, local (warm mypy and tofu caches), every run exit 0 with all 7 gates:

    | Scope | Tests selected | Whole check |
    |---|---|---|
    | `dns` | 17 | 2 s |
    | `milestones` | 8 | 2 s |
    | `labels` | 9 | 2 s |
    | `tofu` | 31 | 2 s |
    | `docs` | 2 | 1 s |
    | full | 892 | 69 s |


## 3. What the guard's matrix depends on

- [x] 3.1 Write `scripts/guard_tests_needed.py` (design D5) and `scripts/tests/test_guard_tests_needed.py`: `true` for
  each guard path, a `test_guard_*.py`, `conftest.py`, `pyproject.toml`, `uv.lock`, `ci.yml` and an empty list;
  `false` for `tofu/dns.json`, `scripts/tofu.py` and `openspec/` paths together; the stdout contract
  (`guard=true\n`). Verify the tests pass, and that they fail when an entry is removed from `DEPENDS_ON`.
- [x] 3.2 Add the test that every file in `tofu/guard_delivery.tf`'s `guard_files` is covered by `DEPENDS_ON`. Verify
  it fails, naming the file, against a copy of `guard_delivery.tf` with an extra delivered file.
  - The tests are in `scripts/tests/test_needs_guard_tests.py`, not `test_guard_tests_needed.py`: a `test_guard_*`
    name would make them one of the guard's own tests, which the matrix runs. 21 pass. Removing `.githooks/`,
    `uv.lock` or `conftest.py` from `DEPENDS_ON` fails 2, 1 and 2 of them. The delivered-file test runs on the real
    `guard_delivery.tf`; a second one shows a `guard_files` list with an extra file is named
    (`["scripts/guard_hooks.toml"]`).

## 4. CI

- [x] 4.1 Add the `changes` job to `.github/workflows/ci.yml`, with `scope`, `check-args` and `guard` outputs, and
  make `check` depend on it (design D4): skipped on `scope=none`, scoped by `check-args`, full when `changes` failed
  or didn't run. Extend `test_required_checks.py` (or a new `test_ci_workflow.py`) to pin these conditions: `check`
  is skipped only on `none`, runs on a failed `changes`, and `changes` is limited to pull requests. Verify the tests
  pass and fail when a condition is changed.
- [x] 4.2 Make `guard-tests` run when `changes` failed, didn't run, or said `guard=true`, and add the `guard tests`
  result job (design D6), its logic in one step whose cases are tested from Python (success, skipped with
  `guard=false`, skipped otherwise, failure, cancelled). Verify those tests pass.
  - 4.1 and 4.2: the conditions are pinned in `scripts/tests/test_ci_workflow.py` (7 mutations, each named), the
    legs' verdict is `guard_tests_needed.py --result`, tested in `test_needs_guard_tests.py` (12 cases).
    `test_required_checks.py` leaves the legs out (`NOT_REQUIRED`) and checks `guard tests` is required and no leg is.
    actionlint (`uvx --from actionlint-py actionlint`) reports nothing. On this branch's own paths the `changes` step
    answers `scope=full`, `check-args=` and `guard=true`.
- [ ] 4.3 Replace the 11 leg contexts with `guard tests` in `tofu/required-checks.json`, and update the `rulesets`
  wording in `README.md` (the example check name). Verify `test_infrastructure_requires_exactly_its_pull_request_jobs`
  passes, and `uv run scripts/tofu.py plan` locally shows only the `infrastructure` ruleset's required checks changing.
- [ ] 4.4 Update `docs/development-workflow.md`'s CI section and `ci.yml`'s header comment to say what this
  repository's CI runs on a pull request and on `main`. Commit the docs edit on its own (with `tasks.md`), and verify
  the commit hook announces `running scripts/check.py --scope docs` and passes.

## 5. Evidence

- [ ] 5.1 Run the differential over the last 40 merged pull requests (design D8): for each, the old selection (full
  check, 11 legs), the new one (scope, selected tests, legs or not), and the check that every test reading a changed
  path is selected or the answer is `full`. Verify zero misses, grep the tests for subprocesses reading scoped files
  (none expected), and record the table, with the time saved, here and in the pull request.
- [ ] 5.2 Open the pull request (`Closes #78`), and verify on its own run: `changes` answers `full` and `guard=true`
  (it changes `ci.yml`), every leg runs, `guard tests` passes, and the plan shows the ruleset change. Record the run
  and plan here.

## Workflow follow-up

- Archive the change on the branch before merging; the owner merges by rebase.
- After the merge, the owner approves main's plan; verify the ruleset requires `guard tests` (`gh api
  repos/troupe-run/infrastructure/rulesets/<id>`), and that the next scoped pull request skips the legs and merges.
- Comment on #78 with the pull request and the archived change, check it's closed, and check its board card is Done.
