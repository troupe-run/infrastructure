# Proposal: quality-gates

## Why

#321 (owner, 2026-11-17) decided that every pull request in troupe, infrastructure and website must pass coverage,
complexity and dependency-audit gates before it can merge, so that #320 can merge safe pull requests without the
owner. Today none of the three repositories measures coverage or complexity, and none audits its dependencies
(#321's survey). #322 builds the coverage gate and #324 the complexity and dependency-audit gates; they land together
because they share a config file, a CI leg and the same diff of what a pull request changed.

## What Changes

- A new gate module, `scripts/quality_gates.py`, written here and delivered to troupe and website like the guard's
  files, so the three repositories (and #320's auto-merge) use one implementation of each measure. Standard library
  only; it runs the measuring tools (coverage.py or Vitest, lizard, pip-audit or npm audit) as processes.
- A per-repository config file, `quality-gates.toml`, not delivered: each repository's thresholds, its packages and
  their coverage baselines live there and nowhere else.
- **Coverage gate.** On one CI leg (Linux, Python 3.15 here and in troupe; website's test run), branch coverage is
  measured per package. A package fails if it falls below its baseline, recorded in the config when the gate lands; a
  package with no baseline must meet a floor. The check prints, per package, the baseline, the measurement and the
  difference.
- **Complexity gate.** In every run of the check, each function the change adds or edits is measured with lizard
  (cyclomatic complexity). It fails when a function is above a generous threshold and is new or more complex than
  before, so existing complex functions are grandfathered until a change makes them worse.
- **Dependency-audit gate.** On the same leg, when the pull request changes a lock file, `pip-audit` (`npm audit` in
  website) fails it on an advisory of high or critical severity that has a fix.
- **Weekly audit report.** A scheduled workflow audits the whole lock file and keeps one issue per repository open
  and up to date with every advisory (any severity, fixable or not), closing it when there are none, and puts it on
  the board.
- Here: `scripts/check.py` runs the gates; CI's `check` job moves to Python 3.15 (Linux 3.12 moves into the guard's
  legs) and runs the leg-only gates; `pyproject.toml` adds coverage, pytest-cov, lizard and pip-audit to the dev
  group; `tofu/guard_delivery.tf` delivers the new module.
- troupe and website adopt the module in their own OpenSpec changes (`quality-gates` in each), after it's delivered.

Not changed: the guard's rules, the 600 s commit-check limit (a local check runs only the cheap complexity gate),
and Claude's review.

## Capabilities

### New Capabilities

- `quality-gates`: the merge gates every governed repository's check runs (coverage, complexity, dependency audit),
  where their thresholds live, and the weekly dependency report.

### Modified Capabilities

- `guard-delivery`: the delivered files include the gate module, so troupe and website run the same measures.
- `ci-apply`: this repository's `check` job runs on Python 3.15 and runs the leg-only gates; Linux 3.12 is covered by
  the guard's legs instead.

## Impact

- New: `scripts/quality_gates.py` and its tests, `quality-gates.toml`, `.github/workflows/dependency-report.yml`.
- Changed: `scripts/check.py`, `.github/workflows/ci.yml`, `pyproject.toml` and `uv.lock` (four dev dependencies,
  so this pull request is itself audited), `tofu/guard_delivery.tf`, `docs/development-workflow.md`.
- A plan that delivers one new file to troupe and website, for the owner's approval.
- CI time: the 3.15 leg's tests run under coverage (sys.monitoring on 3.15, measured in the design).
- troupe gets a `board` environment for its weekly report (`tofu/board.tf`), unless #325 adds it first.
