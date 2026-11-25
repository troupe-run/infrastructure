# Proposal

## Why

The first judged run after #394 (https://github.com/troupe-run/infrastructure/actions/runs/45621303078) opened its five
new `test-quality` issues in module-name order: troupe #517–#521, all `troupe.cli.*`, including `cli.render` at 51.1%,
while many modules at 0% waited. With about 40 modules under the threshold, name order decides which ones wait about 8
nights. Owner decision (2026-11-26, #412): worst first.

## What Changes

- `scripts/mutation_issues.py`'s `plan_repository` judges every module first. It then picks which modules without an
  issue get one of the `max_new_issues` new issues: lowest score first, ties by module name, so the order is stable.
  The rest are named in the summary, as before.
- Updating and closing existing issues is unchanged: every open issue is still kept current each run.
- The `mutation-testing` requirement on the cap gains the order and a scenario.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a run opens its bounded new issues for the lowest scores first.

## Impact

- `scripts/mutation_issues.py` and its test. It runs only in infrastructure (it isn't delivered), so the plan shows no
  changes to troupe.
