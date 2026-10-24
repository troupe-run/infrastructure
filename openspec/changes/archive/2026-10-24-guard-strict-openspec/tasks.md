# Tasks

## 1. Measure OpenSpec, and pin what must not change

- [x] 1.1 With OpenSpec 1.14.3, in a scratch repository, make a main spec whose third requirement is over 500
  characters and an active change whose delta adds a requirement with no scenario. Run
  `openspec validate --all --strict --json --no-interactive` and save its output, exit status and standard error as
  test fixtures under `scripts/tests/fixtures/openspec-strict/` (a failing report and a passing one). Verify the
  failing report's spec issue says `requirements[2]`, so the index counts from 0 in heading order (design D4); if it
  doesn't, correct D4 before going on
- [x] 1.2 Verify the existing `run_ci` and `run_ci_entry` tests in `scripts/tests/test_guard_push_and_ci.py` pass on
  the unchanged guard with no `openspec` on `PATH` (run them with `PATH` stripped of it), so they pin that the
  git-level rules don't depend on the CLI (design D1)

## 2. The rule (design D1-D5)

- [x] 2.1 In `scripts/guard.py`, add `openspec-strict` as a CI-only rule in `RULES`, not in `OVERRIDABLE_RULES`, with
  a comment saying why (D5). Verify `uv run pytest scripts/tests/test_guard_docs.py` fails naming the undocumented
  rule, and that `guard.py override openspec-strict --reason x` is refused by its choice check (a test in
  `scripts/tests/test_guard_overrides.py`)
- [x] 2.2 Add the scope (D3): a pure function from the changed paths, the branch and whether it's a pull request to
  "everything", a set of spec ids and change names, or nothing, with `OPENSPEC_ALL_PATHS` beside it. Move the
  changed-path listing out of `run_ci` into a helper both use. Verify with parametrised tests in a new
  `scripts/tests/test_guard_openspec.py` covering the spec's scope scenarios: no `openspec/` path → nothing; a spec
  path → that spec; an archived change's path → nothing, and the spec its archive commit syncs → that spec; an
  active change deleted at the head → not in scope; `scripts/guard.py` or `.github/workflows/guard.yml` → everything;
  a push to `main` → everything, whatever changed
- [x] 2.3 Add the reading of a report (D2): items with `valid: false` that are in scope are failures; output that
  isn't the expected shape, or whose exit status disagrees with it, is an unreadable result naming the exit status and
  the end of standard error. Verify with tests over the captured fixtures from 1.1, and over each malformed shape
  (not JSON, no `items`, an item without `valid`, exit 1 with every item valid, exit 0 with one failing)
- [x] 2.4 Add the naming (D4): for a spec issue at `requirements[<n>]`, the `n`th `### Requirement:` heading of
  `openspec/specs/<id>/spec.md`, falling back to the path alone when the file or heading is missing. Verify with
  tests: the fixture's third requirement is named; a spec file with fewer headings falls back; a change's issue is
  reported with its delta path under `openspec/changes/<id>/specs/`
- [x] 2.5 Add the refusal (D5): one `Decision` listing every failing item in scope with its issues, and the fix naming
  `openspec validate <id> --type <type> --strict` for one item or `--all` for several, with the version
  `openspec --version` printed. Verify with tests on the refusal's text for one failing spec, one failing change,
  and several; and that a failing spec outside the scope gives no refusal (spec: "A pull request that touches one
  spec while another fails")
- [x] 2.6 Add the run (D1, D2): no `openspec/` or an empty scope runs nothing; otherwise find the CLI with
  `shutil.which("openspec")`, refuse naming `.github/workflows/guard.yml` if it's missing, and run it at the root with
  `OPENSPEC_TELEMETRY=0`, `DO_NOT_TRACK=1` and a 60-second timeout (a constant). Call it from `run_ci_entry` after
  `run_ci`. Verify with tests that inject the runner: missing CLI, timeout, and an empty scope that never calls it;
  and one end-to-end test of `guard.py ci` against a temporary repository with a stub `openspec` (a Python script,
  plus an `openspec.cmd` wrapper on Windows) first on `PATH` that prints the failing fixture, which fails naming the
  requirement
- [x] 2.7 Tag the new tests as `scripts/check-paths.toml` and `guard_pytest` require (fixtures read in-process need
  their scope's tag, if any applies). Verify `uv run pytest scripts/tests -o python_files=test_guard_*.py` passes,
  including the tag check

## 3. The workflow and the docs (design D6)

- [x] 3.1 In `.github/workflows/guard.yml`, add a job-level `OPENSPEC_VERSION: 1.14.3`, `actions/setup-node` (SHA with
  a version comment, an exact Node version of 20.19 or later) and a step installing
  `@fission-ai/openspec@${OPENSPEC_VERSION}` globally before the guard runs, and update the header comment to name
  the new rule. Keep `timeout-minutes: 5`. Verify `uv run pytest scripts/tests/test_required_checks.py
  scripts/tests/test_needs_guard_tests.py` passes, and that the job name `guard (workflow rules)` is unchanged
- [x] 3.2 In `docs/development-workflow.md`, add the `openspec-strict` row (layer: GitHub; what it refuses, its scope,
  that it isn't overridable, the fix), say where the version is pinned, and add the step for moving the pin: run the
  new version over infrastructure's, troupe's and website's main, and name any failure before the delivery plan's
  approval. Update any prose that lists what the `guard` check re-applies. Verify `uv run pytest
  scripts/tests/test_guard_docs.py` passes, and read the section against `run_ci_entry`

## 4. Integration

- [x] 4.1 Push the branch and verify, in the pull request's `guard` run log, that OpenSpec 1.14.3 is installed, every
  spec and active change here is validated (the branch changes `scripts/guard.py`), the rule passes, and the job's
  time is well inside 5 minutes. Record the time in the pull request
- [x] 4.2 With OpenSpec 1.14.3, run the new `guard.py`'s full validation against troupe's and website's `origin/main`
  (scratch copies of each `openspec/`), and verify both pass. Record the counts in the pull request. If either fails,
  stop and tell the owner before the delivery is planned
- [x] 4.3 Run `uv run scripts/check.py` and `openspec validate guard-strict-openspec --strict`, and verify both pass
- [x] 4.4 After rebasing onto `origin/main`, run `uv run scripts/tofu.py plan` and verify it shows only
  `scripts/guard.py` and `.github/workflows/guard.yml` updated in place in troupe and website (four changes). Keep it
  for the pull request

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #123`, the evidence from 1.1, 4.1, 4.2 and the plan from
  4.4. CI must be green on all three OSes before the delivery is planned.
- Tick, archive and rebase onto main's state commit in one push, then ask once for the `plan-pr` approval.
- The owner merges by rebase and approves the `apply` job, which delivers to troupe and website. Check one `guard` run
  on each target's main shows OpenSpec installed and `openspec-strict` passing.
- Comment on #123 with the pull request and the archived change, check it's closed, and check its roadmap card says
  Done.
