# Proposal

## Why

The nightly mutation run of 2026-11-26 (run 45823844707) scored the five `troupe.cli` modules exactly as the night
before, although their unit tests had merged in between (troupe#522, #524). It reopened two fixed modules as troupe#525
and #526 (#418).

The cause, confirmed in mutmut 3.8.1's source and in a throwaway reproduction (below): the kept state (#378) resumes
mutmut, and mutmut keeps a decided result while its function's code is unchanged. New tests only get a stats run (which
function they reach); a result already decided (survived, or reached by no test) is never re-tested. An edited test
body, a changed helper or a deleted test isn't noticed at all. #378's design said "new tests get a stats run" and took
that as enough. It isn't: only the 28-day full refresh would re-score those modules.

## What Changes

- The kept state records, per unit, a fingerprint of every file under the unit's `tests` (a content hash per path).
- Before a unit runs, the files that changed since its state was saved (added, edited or removed) name the tests they
  could change: a changed test file's own tests; the tests in files that import a changed helper, directly or through
  other helpers; every test under a changed `conftest.py`'s directory; and every test, for a changed file that isn't
  Python. Each function those tests reached (by mutmut's kept stats) has all its kept results cleared, so they're
  tested again, and those tests are dropped from mutmut's stats, so mutmut collects what they reach afresh.
- After mutmut's run, any function that gained a test in mutmut's stats (a new test, or a re-collected one reaching it
  now) and still holds a result carried from the kept state has those results cleared. If the budget allows, mutmut
  runs once more and tests just those; otherwise the next night does, since the cleared results are saved.
- State saved before this change has no fingerprint, so its first night counts every test file as changed: every
  unit with tests re-tests what its tests reach, once. Named in the summary.
- The summary says, per unit, how many results were cleared for changed tests and which test files changed.
- A night when no test file changed and no test was added keeps #378's speed-up: nothing is cleared, and mutmut runs
  once.
- The development workflow's "What incremental runs can't see" no longer lists edited tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: an added requirement, that a scheduled run re-tests the kept results its changed tests could
  change.

## Impact

- `scripts/mutation_state.py` (fingerprint, the tests a change names, clearing results and stats) and
  `scripts/mutation_run.py` (the second pass, the summary). Both are delivered to troupe with the pull request report
  (`tofu/guard_delivery.tf`), so the merge is followed by a delivery plan for the owner. The pull request report has no
  kept state, so its behaviour doesn't change.
- `docs/development-workflow.md`, "Each run resumes from the last" and "What incremental runs can't see".
- The workflow (`mutation.yml`) can't run on a pull request. After the merge, a dispatch re-scores troupe:
  `gh workflow run mutation.yml -R troupe-run/infrastructure -f repository=troupe`. That re-tests the `troupe.cli`
  modules, so troupe#525 and #526 close if they pass.

## The reproduction

A toy package (`add`, `double`) in `python:3.12-slim` with mutmut 3.8.1: run 1 with tests that only call the
functions leaves 3 mutants survived; a commit adding asserting tests, then run 2 on the kept `mutants/`, prints
"Found 2 new tests, rerunning stats collection" and still reports all 3 survived (exit codes unchanged in the
`.meta`); run 3 with `mutants/` removed kills all 3. In mutmut's source, `create_file_mutants` keeps
`exit_code_by_key` for every function whose hash is unchanged, and `collect_or_load_stats` only runs stats for new
tests; nothing resets their results.
