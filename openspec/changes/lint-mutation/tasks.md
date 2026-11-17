# Tasks

Load rule for every full check or mutation trial below: check `uptime` first, start only when the 1-minute load is
under 40, and run one at a time. Mutation trials stay small locally (one module); the scheduled job does full runs.

## 0. Owner decisions (design D2, D4, D6)

- [ ] 0.1 The owner confirms how developers install `tflint` (D2), and installs it on this machine
- [ ] 0.2 The owner chooses the credential that files the issues (D4); if not option A, revise
      `specs/mutation-issue-credentials` and these tasks before section 4
- [ ] 0.3 The owner approves, or changes, the thresholds and budget in D6

## 1. `tflint` in the check (design D1, D2)

- [ ] 1.1 Write the tests first in `scripts/tests/test_check.py`: `gates()` lists a `tflint` gate after `tofu validate`
      with `--chdir=tofu --recursive` and the root `.tflint.hcl`; a missing `tflint` exits naming it and the install
      command; a scoped check still runs it. Verify they fail on the base code
- [ ] 1.2 Add the gate to `scripts/check.py` and `.tflint.hcl` (bundled `terraform` ruleset, `recommended` preset, the
      version in a comment). Verify 1.1's tests pass
- [ ] 1.3 Run `tflint` over `tofu/`; fix each finding in `tofu/`, or record it in `.tflint.hcl` with its reason. Verify
      `tflint` exits 0 and `tofu validate` still passes, and that a deliberately unused variable fails the gate
- [ ] 1.4 Install `tflint` in CI's `check` job (`terraform-linters/setup-tflint`, version from `.tflint.hcl`), with a
      test that fails when the workflow's version and `.tflint.hcl`'s differ. Verify the test fails on a mismatch
- [ ] 1.5 README's setup and `docs/development-workflow.md`'s list of gates name `tflint` and how to install it

## 2. Settings and reports (design D3, D5, D6)

- [ ] 2.1 `scripts/mutation.json` with D6's settings and each repository's targets; a loader with a closed schema
      that rejects unknown keys and out-of-range values, wired into the check through its tests. Tests first
- [ ] 2.2 `scripts/mutation_report.py`: mutmut's results (per package) and Stryker's JSON report into the one report
      shape (per module: counts, score, survivors with location and change; finished or not). Tests first, from real
      output captured in a small local trial (one infrastructure module under mutmut, one website file under Stryker),
      saved as fixtures
- [ ] 2.3 Verify the score rule against the spec's scenarios (untested function counts, skipped doesn't, small and
      unfinished modules not judged)

## 3. Issue upkeep (design D5)

- [ ] 3.1 `scripts/mutation_issues.py`: validate each report, find the run's own issues by marker and author, open,
      update, comment, reopen within the window, close on recovery, cap new issues, write the summary and the issue
      URLs. Only print outside GitHub Actions or with `--dry-run`. Tests first, with the GitHub calls faked, covering
      every scenario in `specs/mutation-testing` "Each module under the threshold has exactly one issue" and "A run
      opens a bounded number of new issues"
- [ ] 3.2 Verify a malformed or missing report fails the run naming the repository, after the others are handled
- [ ] 3.3 Verify a dry run against the real repositories (local, read-only, with the trial reports) prints what it
      would do and writes nothing

## 4. Credential, label and workflow (design D3, D4)

- [ ] 4.1 `test-quality` in `tofu/labels/kinds.json`. Verify the plan shows it created in each managed repository and
      nothing else changing
- [ ] 4.2 The App's declaration in `oob/app-installations.json`, the `mutation-issues` environment (main only, no
      bypass) and `TEST_QUALITY_APP_CLIENT_ID` in `tofu/`, with the main-only environment test covering it. Verify the
      check fails when the environment's branch policy is removed
- [ ] 4.3 `.github/workflows/mutation.yml`: weekly schedule and dispatch (`repository`, `dry-run`), the `mutate`
      matrix with no secret on Python 3.15, the `issues` job in `mutation-issues`, the `board` job as `schedules.yml`,
      one concurrency group. Tests: no `pull_request`/`merge_group` trigger, the token's permissions equal the App's
      declaration, the job timeout equals the budget plus 30, the board job's URL check
- [ ] 4.4 `scripts/watched-schedules.json` gains `mutation.yml` (8 days). Verify the schedule watch's tests pass
- [ ] 4.5 The oob README gains the App's creation and key-setting steps; the development workflow doc describes the
      weekly report

## 5. Verification

- [ ] 5.1 The full check passes (`uv run scripts/check.py`), under the load rule
- [ ] 5.2 The draft pull request's CI runs `tflint` and passes; the plan shows only the label, environment, variable
      and policy
- [ ] 5.3 After merge and the owner's apply: dispatch `mutation.yml` with `dry-run`, read its summary, and send the
      scores to the owner to confirm or move the threshold

## Workflow follow-up

- website's ESLint, Prettier and `tsc --noEmit` (the other half of #323) go in a website change on its own branch.
- After merge, comment on #323 and #325 with the PR and the archived change, and check their cards say Done.
