# Design: test the guard on Python 3.14 and 3.15, and require troupe's new jobs

## Context

See proposal.md for why. What shapes the approach:

- `scripts/tests/test_required_checks.py` (`test_infrastructure_requires_exactly_its_pull_request_jobs`) fails unless
  `infrastructure`'s required contexts equal the names its workflows report on a pull request, expanding the
  `guard tests` matrix as GitHub does. A matrix change and its contexts can't be in separate commits without a red
  check in between.
- `tofu/required-checks.json` feeds both "protect main" rulesets (`tofu/repositories.tf`). It changes on GitHub only
  when `main` is applied, after the owner approves that run's plan. A pull request's own CI runs the workflow from its
  head, so this change's pull request already reports the six new `guard tests` jobs before anything requires them.
- troupe's six `check (<os>, Python 3.14|3.15)` jobs report on troupe's `main` since troupe#110 (20e8cd0), and on
  both of troupe's open pull requests (#89, #103) as of 2026-10-16. infrastructure has no open pull requests.
- troupe#110 proved `astral-sh/setup-uv` installs 3.14 and 3.15 on all three GitHub-hosted OSes, with the setup-uv
  version pinned here (v10.3.0). Locally, the guard's 700 tests pass on 3.14.8 and 3.15.0 (macOS, arm64).

## Goals / Non-Goals

**Goals:**
- Every supported Python version runs the guard's tests on every OS, and those jobs are required here and in troupe.
- No pull request is left waiting for a check that never reports.

**Non-Goals:**
- An upper bound on `requires-python` here, or a test that ties the guard's matrix to troupe's bound. troupe's bound
  lives in troupe and can't be read from here (the same reason troupe's required names aren't tested here). The
  matrix in `ci.yml` stays the one place that says which versions the guard is tested on.
- Changing the `"3.12"` tool runtimes or the `>=3.12` floor, ruff target and mypy version (the minimum is what the
  code must stay compatible with).

## Decisions

### D1. One commit: the matrix and all twelve contexts together

The matrix gains `"3.14"` and `"3.15"`, and `required-checks.json` gains the six `guard tests` and six troupe
contexts, in the same commit.

The issue asked for ordering so that a required context exists before it's required. That holds without splitting:
nothing is required until the apply after merge, and by then the jobs exist on both `main`s and on every open pull
request. Splitting the matrix from its contexts would fail the consistency test on the first commit.

Alternative: two pull requests (matrix, then contexts). It costs a second plan and apply cycle and a commit that
fails `check`, and buys nothing the apply's timing doesn't already give.

### D2. Keep ubuntu/3.12 excluded; add no other exclusions

`check` runs every test, the guard's included, on ubuntu with 3.12, so that one leg stays excluded (development-
workflow design D10). 3.14 and 3.15 run on all three OSes: the guard's hooks run on contributors' machines, and
macOS and Windows are where platform differences show. The `guard tests` job count goes from five to eleven.

### D3. Contexts listed in the file's existing order

Each repository's list keeps its current grouping: the `check`/`guard tests` jobs by OS, then by version, then the
other checks. The list is a set to GitHub and to the test; the order is for a reader comparing it with the matrix.

## Risks / Trade-offs

- [3.14 or 3.15 fails on Windows or Linux CI though it passed on macOS locally] → the pull request's CI runs all
  eleven `guard tests` legs before merge. A failure is fixed in the guard or its tests on this branch, as the issue
  scopes in, and noted in tasks.md.
- [A pull request opened from a stale base between merge and apply lacks the new jobs] → it waits for them until
  rebased onto `main`, which re-runs CI. Tasks check both repositories' open pull requests before the apply.
- [3.15 is a .0 release] → the owner chose to add it now (#43, 2026-10-14). A regression in a 3.15.x maintenance
  release shows up as a red required job, which is the point of requiring it.
- [Six more jobs on every push and pull request] → about two minutes each, in parallel. Accepted.

## Migration Plan

1. The pull request runs its CI (eleven `guard tests` legs) and posts its plan: both "protect main" rulesets gain six
   required contexts, nothing else changes.
2. The owner merges by rebase, then approves the `apply` job on `main`.
3. Verify on GitHub that each ruleset lists the new contexts, and that a later pull request in each repository
   reports them.

Rollback: revert the commit by pull request. The apply drops the contexts; until then, the old jobs still report, so
nothing is blocked.
