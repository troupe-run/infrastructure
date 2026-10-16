# Proposal: test the guard on Python 3.14 and 3.15, and require troupe's new jobs

## Why

troupe now supports Python 3.12 to 3.15 (troupe-run/troupe#110, merged as 20e8cd0, widened its bound to
`>=3.12,<3.16`), and the guard's hooks run on contributors' machines under whichever of those versions they have. The
guard is tested only on 3.12 and 3.13, so a break on 3.14 or 3.15 would reach contributors untested. troupe's six new
jobs run and pass on `main`, but none of them is required yet, so a pull request that breaks 3.14 or 3.15 can still
merge there (#43).

## What Changes

- The `guard tests` matrix in `.github/workflows/ci.yml` adds `"3.14"` and `"3.15"` on all three OSes: six new jobs.
  ubuntu/3.12 stays excluded, because the `check` job covers it.
- `tofu/required-checks.json` requires twelve new contexts: the six new `guard tests (<os>, Python 3.14|3.15)` jobs
  for `infrastructure`, and troupe's six `check (<os>, Python 3.14|3.15)` jobs, which already report on troupe's
  `main`.
- The `guard tests` comment says the matrix follows the Python versions troupe supports, and names this change.
- Anything 3.14 or 3.15 breaks in the guard or its tests is fixed. None is known: the guard's 700 tests pass on 3.14.8
  and 3.15.0 on macOS locally.

Out of scope: troupe's own bound, `.python-version`, matrix and fixes (troupe#104, done in troupe#110); dropping 3.12;
the `"3.12"` pinned for tool runtimes in `tofu.yml` and `ci.yml`'s `check` job, and the `>=3.12` floor, ruff target
and mypy version in `pyproject.toml`, which stay at the minimum supported version.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: "Guardrails behave the same on every platform" also covers every Python version troupe
  supports, not only every OS.

`rulesets` needs no change: "Each repository requires its own checks" already requires each guard-tests job and each
of troupe's CI check jobs, so the twelve new names follow from it.

## Impact

- `.github/workflows/ci.yml`: six more `guard tests` jobs on every push and pull request (each about two minutes).
- `tofu/required-checks.json`: the "protect main" rulesets of `troupe` and `infrastructure` each gain six required
  contexts. An apply, after the owner approves its plan, changes both rulesets on GitHub.
- Open pull requests whose head predates these jobs (in either repository) will wait for checks that never report
  once the apply lands, until they're rebased onto `main`.
