# Tasks

Load rule for every full check or mutation trial below: check `uptime` first, start only when the 1-minute load is
under 40, and run one at a time. Mutation trials stay small locally (one module); the scheduled job does full runs.

## 0. Owner decisions (design D2, D4, D6)

- [x] 0.1 The owner confirms how developers install `tflint` (D2). Done: CI first, no local install for now (owner,
      2026-11-17); design D2 and the ci-apply delta record the local skip
- [x] 0.2 The owner chooses the credential that files the issues (D4). Done: option A, a new
      `troupe-run-test-quality` App (owner, 2026-11-17)
- [x] 0.3 The owner approves, or changes, the thresholds and budget in D6. Done: approved, as a ratchet (D7), with W
      (D8) and P (D9) built now and baselines raised by ordinary pull requests (D10: option C; follow-up #326)

## 1. `tflint` in the check (design D1, D2)

- [x] 1.1 Write the tests first in `scripts/tests/test_check.py`: `gates()` lists a `tflint` gate after `tofu validate`
      with `--chdir=tofu --recursive` and the root `.tflint.hcl`; a missing `tflint` fails under `GITHUB_ACTIONS=true`
      naming it, and locally prints the skip notice with the install command and drops only that gate; a scoped check
      still runs it. Verify they fail on the base code
- [x] 1.2 Add the gate to `scripts/check.py` and `.tflint.hcl` (bundled `terraform` ruleset, `recommended` preset, the
      version in a comment). Verify 1.1's tests pass
- [x] 1.3 Run `tflint` over `tofu/` (first in the ready pull request's CI, D2); fix each finding in `tofu/`, or record
      it in `.tflint.hcl` with its reason. First run (2026-11-18, CI run 44130445094): `tflint` read the configuration,
      OpenTofu's `encryption` block included, and the gate failed the check on its 2 findings, both in
      `tofu/modules/repository/main.tf` (`terraform_required_version`, `terraform_required_providers`). Both rules are
      recorded off in `.tflint.hcl`: `tofu/versions.tf` is the one place the versions are pinned. Verified: the next
      CI run (44134274617, at 47289da) passed `tflint` in 0.2 s. `terraform_unused_declarations`, the rule behind the spec's unused-variable scenario,
      stays on in the `recommended` preset
- [x] 1.4 Install `tflint` in CI's `check` job (`terraform-linters/setup-tflint`, version from `.tflint.hcl`), with a
      test that fails when the workflow's version and `.tflint.hcl`'s differ. Verify the test fails on a mismatch
- [x] 1.5 README's setup and `docs/development-workflow.md`'s list of gates name `tflint` and how to install it

## 2. Settings, baselines and reports (design D3, D6, D7)

- [x] 2.1 `scripts/mutation.json` with D6's settings (no reopen window; `tolerance`, `pr_budget_minutes`) and each
      repository's targets; a loader with a closed schema that rejects unknown keys and out-of-range values, wired into
      the check through its tests. Tests first
- [x] 2.2 The `[mutation]` table of `quality-gates.toml`: read through #322's `read_config(path).mutation` (or a
      `tomllib` stand-in under the same name until it's on main), validated as a closed schema; a malformed table fails
      naming the file, module and key. Tests first
- [x] 2.3 `scripts/mutation_report.py`: mutmut's results (per package) and Stryker's JSON report into the one report
      shape (per module: counts, score, survivors with location and change; finished or not). Tests first, from real
      output captured in a small local trial (one infrastructure module under mutmut, one website file under Stryker),
      saved as fixtures
- [x] 2.4 Verify the score rule against the spec's scenarios (untested function counts, skipped doesn't, small and
      unfinished modules not judged)

## 3. Issue upkeep and the ratchet (design D5, D7)

- [x] 3.1 `scripts/mutation_issues.py`: validate each report, judge each module against the threshold and its
      baseline, find the run's own issues by marker and author, open, update, comment, close on recovery, open a new
      one after a closed one, cap new issues, write the summary (with the baselines to raise) and the issue URLs. Only
      print outside GitHub Actions or with `--dry-run`. Tests first, with GitHub's calls faked, covering every scenario
      in `specs/mutation-testing` on issues, the cap and the baseline
- [x] 3.2 Verify a malformed or missing report, or mutation table, fails the run naming the repository, after the
      others are handled
- [x] 3.3 Verify a dry run against the real repositories (local, read-only, with the trial reports) prints what it
      would do and writes nothing

## 4. W: attribution of new survivors (design D8)

- [x] 4.1 Blame each survivor's line at the tested commit and mark it new when its commit isn't an ancestor of the
      previous run's tested commit; tests first, over a scratch git repository built in the test
- [x] 4.2 The issues job finds each new survivor's merged pull request (`commits/<sha>/pulls`, with the run's own
      read-only token), and lists new survivors first in the issue, naming the pull request so GitHub cross-references
      it (option B; whether the run also comments on the pull request is pending the owner, design D8); tests first,
      with GitHub faked. Verify the first run (no previous report) calls nothing new

## 5. P: pull request mutation report (design D9)

- [x] 5.1 `scripts/mutation_pr.py`: changed lines from `git diff --unified=0`, the enclosing Python functions as mutmut
      globs, Stryker `--mutate <file>:<range>` for TypeScript and JavaScript, survivors filtered to changed lines, step
      timings, the report; tests first over a scratch repository and the captured tool output
- [x] 5.2 The comment: found by its marker, edited in place, closed schema on the report, "nothing to mutate" when no
      target changed. Tests first
- [x] 5.3 `.github/workflows/mutation-pr.yml`: ready pull requests only, `mutate` with a read-only token and the
      budget, `comment` with `pull-requests: write` checking out only the base commit, never required, success on survivors. Tests: no
      write permission in `mutate`, only the base commit checked out in `comment`, the timeout follows `pr_budget_minutes`
- [ ] 5.4 Deliver `mutation-pr.yml`, `mutation_pr.py` and `mutation.json` beside the guard's files
      (`tofu/guard_delivery.tf`); verify the delivery tests and the plan list them for troupe and website
- [x] 5.5 Trial P small locally on one changed function in this repository, under the load rule, and record its
      step timings in the design

## 6. Credential, label and weekly workflow (design D3, D4)

- [ ] 6.1 `test-quality` in `tofu/labels/kinds.json`. Verify the plan shows it created in each managed repository and
      nothing else changing
- [x] 6.2 The App's declaration in `oob/app-installations.json`, the `mutation-issues` environment (main only, no
      bypass) in `tofu/test_quality.tf`, with the main-only environment test covering it. Verified: removing the
      environment's branch policy fails the test, naming `mutation-issues` and its policies. The App's creation steps
      are in `oob/README.md` and went to the owner
- [ ] 6.2b `TEST_QUALITY_APP_CLIENT_ID` in `tofu/test_quality.tf`, once the owner has created the App and sent its client
      ID (open on purpose until then: the pull request isn't marked ready before it)
- [x] 6.3 `.github/workflows/mutation.yml`: weekly schedule and dispatch (`repository`, `dry-run`), the `mutate`
      matrix with no secret on Python 3.15 and full history, the previous run's reports downloaded, the `issues` job in
      `mutation-issues`, the `board` job as `schedules.yml`, one concurrency group. Tests: no `pull_request`/
      `merge_group` trigger, the token's permissions equal the App's declaration, the job timeout equals the budget
      plus 30, the board job's URL check
- [x] 6.4 `scripts/watched-schedules.json` gains `mutation.yml` (8 days). Verify the schedule watch's tests pass
- [x] 6.5 The oob README gains the App's creation and key-setting steps; the development workflow doc describes the
      weekly report, the ratchet and P's comment

## 7. Verification

- [x] 7.1 The full check passes (`uv run scripts/check.py`), under the load rule
- [ ] 7.2 The draft pull request's CI runs `tflint` and passes; the plan shows only the label, environment, variable,
      policy and the delivered files
- [ ] 7.3 After merge and the owner's apply: dispatch `mutation.yml` with `dry-run`, read its summary, and send the
      scores and the baselines to record to the owner

## Workflow follow-up

- website's ESLint, Prettier and `tsc --noEmit` (the other half of #323) go in a website change on its own branch.
- After merge, comment on #323 and #325 with the PR and the archived change, and check their cards say Done.
