# Proposal

Issue: #175, section 5a of #170's design.

## Why

#170 makes a minor or patch dependency update cost the owner one merge click. On infrastructure, a pull request that
changes only `uv.lock` or `pyproject.toml` still runs `plan (pull request)` today, because `scripts/plan_needed.py`
plans any path it doesn't know OpenTofu never reads. The run waits in the `plan-pr` environment for the owner's
approval, so a Python tooling bump costs an approval as well as the merge. A Dependabot run has no secrets, so the
approved job then only prints "no plan" anyway.

OpenTofu doesn't read either file. No `.tf` file calls `file()` on them, the guard doesn't deliver them, and every
script the `tofu` workflow runs is run with `uv run --no-project`, which ignores the project's `pyproject.toml` and
`uv.lock`. The owner decided on 2026-10-26 to split by file: Python tooling needs no plan, and the provider lockfile
(`tofu/.terraform.lock.hcl`) keeps its plan and apply, since it changes what OpenTofu runs.

## What Changes

- **`uv.lock` and `pyproject.toml` at the repository root join the paths OpenTofu never reads** in
  `scripts/plan_needed.py`, matched by whole name like `README.md` (design D1). A pull request that changes only
  those, or those and other never-read paths, skips `plan (pull request)`, which counts as passed and asks for
  nothing.
- **The provider lockfile stays planned.** `tofu/.terraform.lock.hcl` is under `tofu/`, so it's planned today; a test
  now names it (design D2).
- **A test pins why the Python files are safe to skip**: every `uv run` in `.github/workflows/tofu.yml` passes
  `--no-project`. A step that runs in the project's environment would make `uv.lock` change what the plan runs, so it
  fails the test, naming the step (design D3).
- **README's list of paths that skip the plan** names the two files.

Out of scope:
- Dependabot's configuration, its issues, and the guard's exemption for its pull requests (the rest of #170).
- `docs/development-workflow.md`'s "Dependabot pull requests" section, which #170's later work rewrites.
- Any other repository: troupe and website have no plan job.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: a pull request that changes only the Python tooling's dependency files isn't planned, while one that
  changes the provider lockfile is.

## Impact

- `scripts/plan_needed.py`: two entries in `NEVER_READ`, and its docstring.
- `scripts/tests/test_plan_needed.py`: tests for the two files, the provider lockfile and the `--no-project` premise.
- `README.md`: the list of paths that skip the plan.
- `openspec/specs/ci-apply/spec.md`, through the delta.
- No change to what OpenTofu declares: this pull request's own plan shows no changes. It is itself planned, since it
  changes `scripts/plan_needed.py`.
- #175 is closed by this change's pull request. #170 stays open.
