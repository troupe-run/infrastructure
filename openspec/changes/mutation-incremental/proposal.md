# Proposal

## Why

#378: troupe's mutation run can't finish in one job. Proving run 44717818525 reached mutant 9,672 of the `troupe`
unit's 19,615 before the 240-minute budget stopped it; the unit needs about 9-10 hours, and troupe's 7 plugin units hold
7,877 more. mutmut 3.8.1 can resume, though (read from its source): it saves each result as its mutant finishes, keeps a
function's results while that function's code is unchanged, and a run given no mutant names skips every stored result.
The owner chose (2026-11-22) to make the scheduled run incremental rather than split it across jobs.

## What Changes

- **mutmut's state is kept between runs, in GitHub's cache:** only each unit's `.meta` files and `mutmut-stats.json`
  (about 3 MB for troupe; the mutated sources regenerate on a fresh checkout). Each run saves a new entry and the next
  restores the newest, keyed by repository and mutmut version.
- **Every run resumes:** each unit runs with no mutant names, so it skips stored results; a run the budget stops keeps
  what it finished, and the next continues. The baseline fills by back-to-back manual dispatches (troupe's unit in about
  3, the plugins in 1), which the runbook in the docs sets out; a dispatch can name one unit; no module globs (they make
  mutmut re-run instead of resume).
- **The schedule becomes nightly;** once filled, a night re-tests only changed functions and anything unfinished.
  `mutation-pr` is unchanged.
- **A full refresh** clears what incremental runs can't see (an edited test, a changed callee under an unchanged
  caller, non-Python changes): `full_refresh_days` (28) in `scripts/mutation.json`, and a `full-refresh` dispatch input.
- **The summary says where results came from** (carried from the restored state, or tested this run, per unit) and names
  mutmut's warning about non-Python changes, which stays on "warn".
- **Lost or unfit state is named and fails visibly:** an evicted or lost cache entry (detected from the previous run's
  record of what it saved), state from another mutmut version or other unit settings, or a file that can't be read
  (only that source file's results are discarded and re-tested). A genuine first fill doesn't fail.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: the scheduled run is nightly and incremental, resuming from kept state, with a periodic full
  refresh, and lost or unfit state named and failing visibly.

## Impact

- `.github/workflows/mutation.yml` (the schedule, the cache restore and save, two dispatch inputs),
  `scripts/watched-schedules.json` (the run's expected age), `scripts/mutation.json` and `scripts/mutation_settings.py`
  (`full_refresh_days`), `scripts/mutation_run.py` (restoring, validating and saving state, the state record),
  `scripts/mutation_issues.py` (the summary's state lines), their tests, and `docs/development-workflow.md` (the
  incremental run and the seeding runbook).
- The plan updates troupe's delivered `scripts/mutation.json`, `mutation_settings.py` and `mutation_run.py`. The weekly
  workflow itself isn't delivered.
