# Tasks

## 1. The guard is tested on 3.14 and 3.15, and those jobs are required

- [x] 1.1 Add the six `guard tests (<os>, Python 3.14|3.15)` contexts for ubuntu, macos and windows to
      `infrastructure` in `tofu/required-checks.json`, in the file's existing order (design D3). Verify
      `uv run pytest scripts/tests/test_required_checks.py` now fails on
      `test_infrastructure_requires_exactly_its_pull_request_jobs`, naming the six missing jobs. That shows the test
      catches a required name no job reports
      Done 2026-10-16: it failed listing exactly the six new `guard tests` names as extra items
- [x] 1.2 Add `"3.14"` and `"3.15"` to the `guard tests` matrix's `python` list in `.github/workflows/ci.yml`, keeping
      only the ubuntu/3.12 exclusion (design D2). Change the job's comment to say the matrix follows the Python
      versions troupe supports (3.12 to 3.15, troupe-run/troupe#110) and to name this change. Verify
      `uv run pytest scripts/tests/test_required_checks.py` passes
      Done 2026-10-16: 11 passed
- [x] 1.3 Add troupe's six `check (<os>, Python 3.14|3.15)` contexts to `troupe` in `tofu/required-checks.json`
      (design D3). These can't be tested here, so verify each name against what troupe's `main` reports:
      `gh api repos/troupe-run/troupe/commits/main/check-runs --jq '.check_runs[].name'` lists all six, spelled the
      same. Record the output in this task
      Done 2026-10-16: troupe's `main` (fede63f) reports `check (<os>, Python <v>)` for ubuntu-latest, macos-latest
      and windows-latest on 3.12, 3.13, 3.14 and 3.15, and `diff` of those twelve names against troupe's declared
      `check` jobs is empty
- [x] 1.4 Run the guard's tests on 3.14 and 3.15 locally, each in its own environment
      (`UV_PROJECT_ENVIRONMENT=<scratchpad>/venv-<v> uv run --locked --python <v> pytest scripts/tests
      -o 'python_files=test_guard_*.py'`), and run `uv run scripts/check.py`. Verify both pass, and record the counts.
      If either version fails, fix the guard or its tests here, with a test named for the behaviour, before going on
      Done 2026-10-16 (macOS arm64): 3.14.8, 700 passed in 80.41s; 3.15.0, 700 passed in 79.97s. `check.py`: all
      gates passed. Nothing needed fixing
- [ ] 1.5 Run `tofu fmt -check` and `tofu validate`, then a local plan after fast-forwarding onto `origin/main`.
      Verify the plan changes only the two "protect main" rulesets (`troupe`, `infrastructure`), each by the six new
      required contexts, and record its summary line

## 2. Evidence on GitHub

- [ ] 2.1 Push the branch and open the pull request (`Closes #43`). Verify all eleven `guard tests` legs report and
      pass on it, and that its posted plan matches 1.5's. Fix anything a leg finds on this branch (design, Risks) and
      record it here
- [ ] 2.2 Before the apply, list open pull requests in troupe and infrastructure, and verify each reports the new
      jobs, or note which need a rebase (design, Risks)

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging. The owner merges by rebase and approves `main`'s `apply` job.
- After the apply, verify with `gh api repos/troupe-run/<repo>/rulesets/<id>` that each "protect main" ruleset lists
  the new contexts, and that the next pull request in each repository reports them.
- Comment on #43 with the pull request and the archived change, check it's closed, and set its card to Done.
