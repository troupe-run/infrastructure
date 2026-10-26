# Tasks

## 1. Pin what must stay the same

- [x] 1.1 Before changing `scripts/plan_needed.py`, add to `scripts/tests/test_plan_needed.py` the cases that must keep
  planning (design D1, D2): `tofu/.terraform.lock.hcl` alone; `tofu/.terraform.lock.hcl` with `uv.lock`;
  `scripts/pyproject.toml`, `tofu/uv.lock` and `uv.lock.bak` (not the root files). Verify they pass on the unchanged
  script with `uv run pytest scripts/tests/test_plan_needed.py`. Result: `test_the_provider_lockfile_plans_alone_or_with_the_python_lockfile` and `test_a_python_tooling_file_outside_the_root_or_renamed_plans` (which also covers `pyproject.toml.orig`). 17 passed on the unchanged script

## 2. Skip the plan for the Python tooling files (design D1)

- [x] 2.1 Add a test that `uv.lock` alone, `pyproject.toml` with `uv.lock`, and those with `docs/x.md` don't plan, and
  add `pyproject.toml` and `uv.lock` to the never-read case in
  `test_a_pull_request_of_only_never_read_files_isn_t_planned`. Verify it fails on the unchanged script, then add the
  two entries to `NEVER_READ` with a comment, and the docstring's reason (the `tofu` workflow runs its scripts without
  the project), and verify every test in `test_plan_needed.py` passes, including
  `test_every_path_opentofu_reads_is_planned` and 1.1's cases. Result: `test_a_python_tooling_bump_at_the_root_isn_t_planned` and the extended never-read case failed on the unchanged script (4 failed, 16 passed). With the two entries, 20 passed
- [x] 2.2 Extend `test_the_script_prints_a_github_output_line` with `uv.lock\npyproject.toml\n` giving `plan=false`
  and `uv.lock\ntofu/.terraform.lock.hcl\n` giving `plan=true`. Verify it passes. Result: 20 passed

## 3. Pin the --no-project premise (design D3)

- [x] 3.1 Add a test to `test_plan_needed.py` that parses `.github/workflows/tofu.yml` with PyYAML and checks that
  every `uv run` in each step's `run` text passes `--no-project`, failing with the job, the step's name and D3's two
  ways out. Its docstring names the limit (`uvx`, `uv tool run` aren't caught). Verify it passes, that it finds at
  least one `uv run` in each of the `pr-plan`, `main-plan` and `apply` jobs (so it can't pass by finding none), and
  that deleting `--no-project` from one step in a scratch copy of the workflow makes it fail naming that step (check
  by hand, then restore). Result: `test_every_uv_run_in_the_tofu_workflow_passes_no_project` (21 `uv run`s, in `pr-plan`, `plan`, `oob` and `apply`: the main plan's job id is `plan`, not `main-plan`). The failure case is also a permanent test, `test_a_uv_run_without_no_project_is_reported_naming_its_job_and_step`, which also checks a commented-out `uv run` isn't counted. By hand: a scratch copy of `tofu.yml` with `--no-project` removed from the apply step reported `('apply', 'Apply the approved plan', False)`. 22 passed

## 4. Documentation

- [x] 4.1 Add `pyproject.toml` and `uv.lock` to README's list of files that skip the plan ("Open a pull request"),
  saying the provider lockfile is still planned. Verify `git grep -n "scripts/tests/\`, \`README.md\`" README.md`
  shows the updated list and `uv run scripts/check.py` passes. Result: README.md:103 lists both; check: all gates passed

## 5. Verify on GitHub

- [x] 5.1 Open the pull request (`Closes #175`). Verify the `does it need a plan?` job outputs `plan=true` for it
  (it changes `scripts/plan_needed.py`), and, once the owner approves the `plan-pr` run, that the posted plan shows no
  changes. Record the run links here. Result: #179. In [run 40333492107](https://github.com/troupe-run/infrastructure/actions/runs/40333492107), `does it need a plan?` passed and `plan (pull request)` waited for `plan-pr`, which it does only on `plan=true`. After the owner approved, the [plan for 23dcc7f](https://github.com/troupe-run/infrastructure/pull/179#issuecomment-6417685832) showed no changes and no modes to set. Every other check passed
- [x] 5.2 Check the skip against a real bump: in a scratch clone of this branch, commit `uv lock --upgrade-package
  <one dev dependency>`, and pipe `git diff --name-only HEAD~1...HEAD` to the branch's `scripts/plan_needed.py`, as
  the `changes` job does. Verify it prints `plan=false`, and `plan=true` once `tofu/.terraform.lock.hcl` is touched in
  the same diff. Record the output here. Result: in a scratch clone of e5c9480, `uv lock --upgrade-package` took ruff 0.17.0 → 0.17.2 and hypothesis 6.169.0 → 6.170.11 (pytest-xdist was current). The diff `uv.lock` printed `plan=false`; with `tofu/.terraform.lock.hcl` also changed, `plan=true`. The clone is deleted

## Workflow follow-up

- Archive the change on the branch before the owner merges, batching the archive with the 5.1 record so the plan is
  approved once.
- After the merge, on the first pull request that changes only `uv.lock` (a Dependabot `uv` bump, from #170's
  work), check `plan (pull request)` is skipped and shows as passed, and note it on #170.
- After the merge, check #175 is closed and its card is Done, and comment on it with the PR and the archived change.
