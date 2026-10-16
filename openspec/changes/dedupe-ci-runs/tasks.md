# Tasks

## 1. CI runs once per pull request and once per merge, pinned by tests

- [x] 1.1 Add the two tests from design D3 to `scripts/tests/test_required_checks.py`, next to
      `test_guard_re_runs_when_a_pull_request_is_renamed_and_still_runs_on_every_push`, each named for what its body
      checks. First: `ci.yml` runs on `pull_request` with no path filter, and on `push` to `["main"]` only, with
      `paths-ignore` exactly `["tofu/terraform.tfstate"]`, a path `tofu.yml` names in its state-commit skip. Second:
      every branch `tofu.yml`'s `workflow_run` follows is listed by name in `ci.yml`'s `push` branches (no glob
      matching), and its `workflows` names `ci.yml`'s `name`. Verify that against the current `ci.yml` both fail,
      naming `["**"]` and the missing `paths-ignore`. Record the output here
      Done 2026-10-16: `test_ci_tests_pull_requests_unfiltered_and_main_s_pushes_except_the_state_commit` failed with
      `push runs on ['**'], not ['main']` and `push ignores None, not ['tofu/terraform.tfstate']`;
      `test_main_s_plan_follows_the_ci_run_main_s_pushes_start` failed with `tofu.yml follows CI on ['main'], which
      ci.yml's pushes don't list`. The checks are functions returning their problems, so 1.3 can run them on
      in-memory copies of the workflows
- [x] 1.2 In `.github/workflows/ci.yml`, change the `push` trigger to `branches: [main]` with
      `paths-ignore: ["tofu/terraform.tfstate"]` (design D1, D2), and rewrite the top comment: it tests each pull
      request once (merged onto `main`) and `main` after every merge, which `tofu.yml`'s plan of `main` follows, and it
      skips the App's state commit, which the plan skips too (#66, this change). Verify
      `uv run pytest scripts/tests/test_required_checks.py` passes, including
      `test_infrastructure_requires_exactly_its_pull_request_jobs` (the required names don't change), and that
      `uv run scripts/check.py` passes
      Done 2026-10-16: `test_required_checks.py`, 14 passed. `check.py`: all gates passed. The old comment's "plans
      run on the owner's machine" line was out of date (CI plans since ci-apply) and is gone
- [x] 1.3 Check the tests catch the drifts design D3 names: on scratch copies of the workflows (not the real files),
      rename `CI`, and rename the state file in `ci.yml`'s `paths-ignore` only, and verify the matching test fails
      on each, naming the mismatch. Record the results here
      Done 2026-10-16, as committed tests on in-memory copies of the workflows (the file's existing idiom, as in
      `test_a_renamed_matrix_leg_no_longer_matches_the_required_names`), so the drift stays checked: renaming `CI`,
      pushes without `main`, a different state path, and a path filter on `pull_request` each produce exactly the
      expected problem. `test_required_checks.py`: 18 passed; mypy --strict and ruff clean
- [x] 1.4 Check that no doc describes CI as running on every push: `grep -rn -i "every push" README.md docs
      .github/workflows`. Verify the only hits are about `guard` and the `pre-push` hook, which don't change
      Done 2026-10-16: two hits, `docs/development-workflow.md:15` (`pre-push`) and `:17` (`guard`). README's "guard and
      CI runs" (line 229) is about receiving repositories' runs on delivered commits on `main`, which still run

## 2. Evidence on GitHub

- [ ] 2.1 Push the branch and open the pull request (`Closes #66`). Verify on its head commit, with
      `gh api repos/troupe-run/infrastructure/commits/<sha>/check-runs --jq '.check_runs[].name' | sort | uniq -c`,
      that `check` and each of the eleven `guard tests` legs report exactly once and pass, and that
      `guard (workflow rules)` still reports twice (push and pull request). Record the counts here
- [ ] 2.2 After the owner approves the pull request's plan run, verify `plan (pull request)` passes with no changes,
      and record its summary line

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging. The owner merges by rebase.
- After the merge, verify CI ran on `main`'s new head as a `push` run
  (`gh run list -R troupe-run/infrastructure --workflow ci.yml --branch main --event push --limit 1`), and that
  `tofu.yml`'s `plan (main)` started from it.
- At the next merge whose apply commits state, verify `gh run list -R troupe-run/infrastructure --commit <state sha>`
  lists `guard` and no `CI` run. Record it on #66.
- Comment on #66 with the pull request and the archived change, check it's closed, and set its card to Done.
