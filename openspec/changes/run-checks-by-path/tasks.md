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
- [x] 4.3 Replace the 11 leg contexts with `guard tests` in `tofu/required-checks.json`, and update the `rulesets`
  wording in `README.md` (the example check name). Verify `test_infrastructure_requires_exactly_its_pull_request_jobs`
  passes, and `uv run scripts/tofu.py plan` locally shows only the `infrastructure` ruleset's required checks changing.
  - 4.3: `test_infrastructure_requires_exactly_its_pull_request_jobs` passes. The local plan couldn't run (1Password
    timed out waiting for the owner's Touch ID: `authorization timeout`), so the plan is #83's, approved by the owner
    (run 39034742492): `Plan: 0 to add, 1 to change, 0 to destroy`, only
    `module.repo_infrastructure.github_repository_ruleset.main[0]` updated in place, its 11 `guard tests (<os>,
    Python <v>)` contexts removed and `guard tests` added.
- [x] 4.4 Update `docs/development-workflow.md`'s CI section and `ci.yml`'s header comment to say what this
  repository's CI runs on a pull request and on `main`. Commit the docs edit on its own (with `tasks.md`), and verify
  the commit hook announces `running scripts/check.py --scope docs` and passes.
  - 4.4: the docs commit (513dfb3 before the rebase onto main, 43c5155 after) printed `guard: only README.md, docs/**
    and openspec/** are staged; running scripts/check.py --scope docs instead of the full check` and `passed in 2s`.

## 5. Evidence

- [x] 5.1 Run the differential over the last 40 merged pull requests (design D8): for each, the old selection (full
  check, 11 legs), the new one (scope, selected tests, legs or not), and the check that every test reading a changed
  path is selected or the answer is `full`. Verify zero misses, grep the tests for subprocesses reading scoped files
  (none expected), and record the table, with the time saved, here and in the pull request.
  - 2026-10-17. Only 34 pull requests have ever merged here (#3 to #82), so all 34 are in it, not 40. Each test's
    reads and tags were recorded over the full suite (934 tests, before the rebase onto main added one, which
    `test_dns.py`'s module tag covers). For each pull request: the scope `check-scope` gives its paths, the tests that
    scope selects, the tests that read any changed path, and those not selected. **Misses: 0.** 31 pull requests
    still run the full check (each changed a script, a workflow or another path in no scope); 3 are scoped, none
    skipped. The legs are skipped on 19 of 34. The tests that use subprocesses read scoped files only in temporary
    repositories, never this one's.

    | PR | Paths | Scope | Tests run (of 934) | Tests reading a changed path | Missed | Legs (of 11) | Title |
    |---|---|---|---|---|---|---|---|
    | #3 | 52 | full | 934 | 38 | 0 | 11 | feat: adopt the troupe-run org into OpenTofu, with a clean p |
    | #7 | 12 | full | 934 | 10 | 0 | 0 | feat: protect main on every managed repository with a rulese |
    | #9 | 48 | full | 934 | 65 | 0 | 11 | feat: the development workflow and its guard live here, and  |
    | #10 | 22 | full | 934 | 21 | 0 | 0 | ci-apply: plan and apply the org from GitHub Actions |
    | #12 | 10 | full | 934 | 11 | 0 | 0 | fix-state-commit: commit CI's state with a tested script, an |
    | #13 | 13 | full | 934 | 12 | 0 | 11 | rename-website: troupe-run.github.io becomes website |
    | #17 | 34 | full | 934 | 29 | 0 | 11 | required-checks: required CI, guard, DCO and plan checks; an |
    | #18 | 10 | full | 934 | 32 | 0 | 11 | refuse-admin-merge: allow-list agents' gh commands, and refu |
    | #20 | 22 | full | 934 | 23 | 0 | 0 | feat: org-default PR template and issue forms in .github |
    | #23 | 7 | full | 934 | 2 | 0 | 0 | fix: drop the duplicate security link from the org's issue c |
    | #24 | 15 | full | 934 | 16 | 0 | 0 | feat: declare troupe's capability labels here, changed by pu |
    | #27 | 5 | labels | 9 | 1 | 0 | 0 | feat(tofu): add cap:client-protocol and cap:runs to troupe's |
    | #28 | 12 | full | 934 | 1 | 0 | 0 | feat: say what each of troupe's cap: labels covers, and repo |
    | #32 | 9 | full | 934 | 31 | 0 | 11 | feat(guard)!: one way per write — refuse GraphQL mutations a |
    | #36 | 6 | full | 934 | 1 | 0 | 0 | chore(labels): refresh cap:platform and cap:protocol, add ca |
    | #37 | 11 | full | 934 | 44 | 0 | 11 | feat(guard): pass release-please's PR narrowly, and check PR |
    | #38 | 10 | full | 934 | 32 | 0 | 11 | feat(guard): grant the plain gh commands the guard allows, s |
    | #40 | 11 | full | 934 | 13 | 0 | 0 | ci(tofu): plan main every day, so a forged delivery shows wi |
    | #41 | 18 | full | 934 | 11 | 0 | 0 | feat(tofu): declare troupe's release App, its environment, v |
    | #44 | 10 | full | 934 | 31 | 0 | 11 | feat(guard): open the release-please exemption on troupe onl |
    | #48 | 19 | full | 934 | 38 | 0 | 11 | feat(guard): run only what a commit's paths need |
    | #49 | 18 | full | 934 | 47 | 0 | 11 | fix(guard): trust a release branch's name only where troupe  |
    | #50 | 8 | full | 934 | 22 | 0 | 11 | ci: test the guard on Python 3.14 and 3.15, and require thos |
    | #56 | 9 | docs,tofu | 35 | 1 | 0 | 0 | feat(tofu): declare the website's github-pages environment a |
    | #57 | 13 | full | 934 | 10 | 0 | 0 | feat(tofu): declare the website's GitHub Pages settings |
    | #64 | 25 | full | 934 | 17 | 0 | 0 | feat(tofu): govern the website with the guard, without DCO |
    | #65 | 20 | full | 934 | 3 | 0 | 11 | feat: turn on Dependabot and secret scanning in every reposi |
    | #67 | 8 | full | 934 | 19 | 0 | 11 | ci: test a pull request once, and main except its state comm |
    | #70 | 14 | full | 934 | 3 | 0 | 0 | feat: declare the release milestones in every managed reposi |
    | #71 | 16 | full | 934 | 42 | 0 | 11 | feat(guard): delivered files keep their source's mode |
    | #74 | 26 | full | 934 | 18 | 0 | 0 | feat: manage troupe.run's DNS in Cloudflare as code |
    | #77 | 4 | dns | 17 | 5 | 0 | 0 | fix(dns): publish troupe.run's new Pages verification record |
    | #79 | 12 | full | 934 | 6 | 0 | 0 | feat(dns): declare troupe.run's Universal SSL setting with i |
    | #82 | 11 | full | 934 | 6 | 0 | 0 | fix(dns): turn troupe.run's Universal SSL off |

- [x] 5.2 Open the pull request (`Closes #78`), and verify on its own run: `changes` answers `full` and `guard=true`
  (it changes `ci.yml`), every leg runs, `guard tests` passes, and the plan shows the ruleset change. Record the run
  and plan here.
  - #83, CI run 39034742545: `what does it need?` answered `scope=full`, `check-args=` and `guard=true` (the pull
    request changes `ci.yml`). `check` passed, all 11 legs passed under their expanded names, and `guard tests`
    passed. `plan (pull request)`, `guard (workflow rules)` and DCO passed. The plan is as in 4.3.

## Workflow follow-up

- Archive the change on the branch before merging; the owner merges by rebase.
- After the merge, the owner approves main's plan; verify the ruleset requires `guard tests` (`gh api
  repos/troupe-run/infrastructure/rulesets/<id>`), and that the next scoped pull request skips the legs and merges.
- Comment on #78 with the pull request and the archived change, check it's closed, and check its board card is Done.
