# Design

## Context

`scripts/plan_needed.py` (required-checks design D2) lists what OpenTofu is known never to read, and plans anything
else. `test_every_path_opentofu_reads_is_planned` derives what OpenTofu reads (every file under `tofu/`, the literal
paths in `file()` calls, the guard's delivered files and `org-profile/`) and asserts each one plans. See proposal.md
for why the Python files should join the list.

What the `tofu` workflow does with Python today: `setup-uv` installs uv and Python 3.12, then every step runs a script
with `uv run --no-project` (`tofu.py`, `plan_secrets.py`, `hook_modes.py`, `plan_checks.py`, `plan_comment.py`,
`oob.py`, `commit_state.py`). With `--no-project`, uv doesn't read `pyproject.toml` or `uv.lock` and installs nothing
from them, so the scripts run on the standard library. No file under `tofu/` or `.github/` names either file.

The repository's only `pyproject.toml` and `uv.lock` are at the root.

## Goals / Non-Goals

**Goals:**
- A pull request changing only the root `pyproject.toml` and `uv.lock` (with or without other never-read files) skips
  the plan.
- The skip can't silently become wrong if the workflow later uses the project's environment.

**Non-Goals:**
- Skipping the guard's tests or `check` for these files. A bump still runs ruff, mypy and the tests in CI
  (`ci.yml` runs `uv run scripts/check.py` and `uv run pytest` in the project's environment), which is how a bump is
  tested.
- Changing the `plan (main)` job. It plans after every push to `main`; after a Python-only merge that plan has no
  changes and ends without asking for an approval, so the merge is still the owner's only click.

## Decisions

### D1: Two whole-name entries in NEVER_READ

Add `"pyproject.toml"` and `"uv.lock"` to `NEVER_READ`, matched as whole paths like `README.md`. So
`scripts/pyproject.toml` or `tofu/uv.lock` still plans, which the spec's "only the root files" scenario pins.
The module's docstring says why these two are safe: the workflow runs its scripts without the project.

Alternatives:
- *A `*.lock`/`pyproject.toml` match anywhere.* Rejected: `tofu/.terraform.lock.hcl` is a lockfile too, and a
  pattern risks catching a file OpenTofu reads. The list stays "known never read", by name.
- *Skip the plan for every Dependabot pull request.* Rejected: the provider lockfile must plan (owner, 2026-10-26),
  and an author is not a path.

### D2: The provider lockfile is named in a test

`tofu/.terraform.lock.hcl` already plans: it's under `tofu/`, and `paths_opentofu_reads()` includes it
(`Path.rglob` returns dotfiles). Add a test that names it, alone and together with `uv.lock`, so the owner's split
reads as a test rather than as a consequence of `rglob`.

### D3: A test pins the `--no-project` premise

The skip is right only while no step of `tofu.yml` runs in the project's environment. If one did, `uv.lock` would
choose the code that runs with the App's key and the state passphrase, and a bump could change a plan or an apply
without a plan being shown.

A test reads `.github/workflows/tofu.yml` and checks that every `uv run` in a `run:` block passes `--no-project`. It
fails naming the job and step otherwise. The message says the two ways out: run the step without the project, or take
`pyproject.toml` and `uv.lock` back out of `NEVER_READ`.

The test parses the workflow with PyYAML (a dev dependency already used by the tests) and scans each step's `run`
text for `uv run`, rather than grepping the file, so a comment mentioning `uv run` doesn't count. `uv` invoked another
way (`uvx`, `uv tool run`, `python -m`) isn't caught; none is used today, and the test's docstring names the
limit.

Alternatives:
- *No test; a comment in `tofu.yml`.* Rejected: a comment doesn't fail, and the mistake it guards against costs a
  plan the owner never saw.
- *Plan anyway when `pyproject.toml` changes, skip only `uv.lock`.* Rejected: `pyproject.toml` changes the lock's
  inputs but nothing the workflow runs, for the same `--no-project` reason, and Dependabot's `uv` updates edit both.

The test reads a workflow file, which is in no `check-paths.toml` scope, so it needs no scope tag.

## Risks / Trade-offs

- [A later workflow step uses the project's environment] → D3's test fails in CI on that pull request, naming the step.
- [Another tool reads `pyproject.toml` during a plan, e.g. a script parsing it] → None does today: no script the `tofu`
  workflow runs opens it (`guard_tests_needed.py` names it only as a path, for `ci.yml`); `test_every_path_opentofu_reads_is_planned` covers OpenTofu's own reads. A script reading it would be a change
  to a planned file (`scripts/*.py`), reviewed with its plan.
- [This pull request itself] → it changes `scripts/plan_needed.py`, which plans, so it takes one `plan-pr` approval.
  Its plan shows no changes.

## Migration Plan

None. Once merged, the next pull request that changes only the two files skips its plan. Rollback is reverting the
two entries.
