# Proposal: Run only the checks a change's paths need, locally and in CI

## Why

#74 and #77 changed `tofu/dns.json`, `tofu/*.tf` and two scripts, and no guard file. Yet every commit outside
`openspec/` ran the whole `scripts/check.py` (about 75 seconds, and 160 seconds measured on 2026-10-17 for the 889
tests alone), and every pull request ran it again in CI plus the guard's tests on 11 OS and Python legs (#78). The
machinery to do less already exists: `scripts/check-paths.toml` takes scopes, `check.py --scope` narrows the tests,
`guard_pytest` fails a test that reads a scope's path without its tag, and `guard.py check-scope` answers "what do
these paths need" for CI. This repository declares no scope, and its CI doesn't ask.

A declaration change isn't test-free: `tofu/dns.json` is validated by `test_dns.py`, `milestones.json` and `labels/`
by theirs. The aim is the right tests, not none.

## What Changes

- **Scopes for the declarations**, in `scripts/check-paths.toml`: `dns` (`tofu/dns.json`), `milestones`
  (`tofu/milestones.json`), `labels` (`tofu/labels/**`), `tofu` (each `tofu/*.tf` file by name, and
  `tofu/modules/**`), and `docs` (`docs/**`, `README.md`, `CLAUDE.md`). The tests that read those files are tagged,
  which `guard_pytest` already enforces on every run. A scoped check still runs every other gate (ruff, mypy, `tofu
  fmt`, `tofu validate`), as it does today. The pre-commit hook needs no change: it already reads the declaration.
- **CI's `check` job asks `guard.py check-scope`** with the pull request's changed paths, and runs `check.py` with
  the scopes it answers, nothing when it answers `none`, or the full check. A path in no group, an empty list or a
  changed declaration still means the full check.
- **The guard's 11-leg test matrix runs only when a path it depends on changes**: the guard's delivered files, its
  tests and their `conftest.py`, the declaration, the Python project files (`pyproject.toml`, `uv.lock`), and
  `ci.yml` itself. That list is kept in one script, as `plan_needed.py` keeps the plan's, and a test fails if a
  delivered guard file is missing from it.
- **One required `guard tests` check replaces the 11 per-leg ones.** GitHub reports a skipped matrix job under its
  unexpanded name (`guard tests (${{ matrix.os }}, …)`), so the per-leg required checks would wait forever on a pull
  request that skips them. A small job that always runs passes when the legs passed, or were skipped because nothing
  they test changed, and fails otherwise. `tofu/required-checks.json` changes, so this pull request has a plan that
  changes the `infrastructure` ruleset. The skipped-matrix behaviour is proven on a throwaway repository first.
- **`main` keeps the full check and every leg after each merge**, as a backstop: `main` doesn't require a branch to
  be up to date, so its merged tree may be one no pull request tested, and a guard delivery is planned only after CI
  is green on all three OSes for the delivered commit.

Out of scope:

- **The guard itself.** `check-scope`, `check.py --scope` and `guard_pytest` already do what's needed, so no
  delivered file changes and nothing is delivered to troupe or the website.
- **troupe's CI.** If troupe wants the same, that's troupe's own issue (#78's notes).
- **The plan's path filter** (`scripts/plan_needed.py`), which is already filtered and answers a different question.
- **Scopes for Python sources** (`scripts/*.py`). A test reads a module by importing it, once per process, so the
  tag check can't see which tests depend on it. A change to a script keeps running the full check.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: a new requirement that this repository's check runs only what a change's paths need, before a commit
  and on a pull request; a new requirement that the guard's matrix runs only when what it tests changes, behind one
  `guard tests` check; and "CI tests each pull request once, and main after every push" says that `main` still runs
  everything.
- `rulesets`: "Each repository requires its own checks" requires the one `guard tests` check for `infrastructure`,
  not each leg.

`development-workflow` needs no change: its requirements for the declaration, `check-scope` and the tag check are
already written for any repository, and this change only uses them.

## Impact

- `scripts/check-paths.toml`: five scopes, and the comment saying why Python sources aren't scoped.
- `scripts/tests/`: scope markers on the tests that read the scoped files (`test_dns.py`, `test_milestones.py`,
  `test_labels.py`, part of `test_org_profile.py`, `test_plan_needed.py`, `test_required_checks.py`, part of
  `test_guard_push_and_ci.py`, `test_guard_docs.py`); tests for the new script and the CI wiring; the differential
  evidence over past pull requests.
- A new `scripts/guard_tests_needed.py` (standard library, run with the runner's `python3` like `plan_needed.py`).
- `.github/workflows/ci.yml`: a `changes` job, the scoped `check`, the conditional matrix and the `guard tests` gate.
- `tofu/required-checks.json`: 11 contexts become one. The pull request's plan updates the `infrastructure` ruleset
  in place; the owner approves the apply as usual.
- `README.md` and `docs/development-workflow.md`: the required check's name, and what this repository's CI runs.
