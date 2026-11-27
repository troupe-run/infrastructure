# Tasks

## 1. Which tests a change names (D1, D2)

- [x] 1.1 Tests first (`scripts/tests/test_mutation_retest.py`), each failing before the code: the fingerprint of a
      unit's tests (skips `__pycache__`/`.pyc`); added, edited and removed files from two fingerprints; a changed test
      file names itself; a helper imported through another helper names the importing test file (`import x`, `from x
      import y`, `from . import x`); a changed `conftest.py` names the test files under its directory only; a
      non-Python change names every test file; node ids (in the form mutmut 3.8.1 wrote in the reproduction) map to
      their files for a package's unit and for a root unit.
- [x] 1.2 `mutation_state.py`: the fingerprint, the changed files and the tests they name. `uv run pytest
      scripts/tests/test_mutation_retest.py` passes.

## 2. Clearing before and after the run (D3, D4, D5)

- [x] 2.1 Tests first: `restore` with a changed test file clears every result of the functions its tests reached
      (killed included), keeps the others, and removes those tests from the stats; no change clears nothing and leaves
      the stats byte for byte; a manifest entry without `tests_fingerprint` counts every test as changed and says so;
      `save` writes `tests_fingerprint`. The test that a new test file's survivors are cleared after the run, and that
      a function whose hash changed or whose results were already `null` isn't, fails on main's code (the #418 case).
- [x] 2.2 `restore` and a post-run step in `mutation_state.py` do D3 and D4; `UnitState` gains `tests_changed`,
      `cleared_for_tests` and `retested` (D6). The tests pass.

## 3. The second pass and the summary (D4, D6)

- [x] 3.1 Tests first (`test_mutation_run.py`'s recorder): when the post-run step clears results, `run_mutmut` runs
      `mutmut run` a second time within the remaining budget; not when nothing was cleared, mutmut exited -1 or the
      unit was unreached; the report reads the results after the last pass. The summary's state section shows the
      cleared count, the first changed paths, and when cleared results wait for the next night.
- [x] 3.2 `run_mutmut` and `mutation_issues.state_section`. The tests pass.

## 4. Proof against real mutmut

- [x] 4.1 A container trial (`python:3.12-slim`, mutmut 3.8.1, a toy package, never troupe's suite on the host): run
      with weak tests, keep the state through `save`/`restore`, add asserting tests in a new file, run through
      `run_mutmut`: the survivors are killed in that run. Then edit a helper only: the functions its importers reach are
      re-tested, the rest carried. Then change nothing: one pass, nothing cleared. Record the commands and output in
      the PR (2026-11-27: night 2 added a test file and mutmut ran twice, killing `add`'s survivor in
      that run; night 3 changed nothing, one pass; night 4 edited a helper, re-testing `double`/`half` and
      carrying `add`; night 5 edited a test, re-testing what it reaches).

## 5. Docs and check

- [x] 5.1 `docs/development-workflow.md`: "Each run resumes from the last" says changed tests clear what they reach
      and the second pass; "What incremental runs can't see" drops edited tests; the module docstring of
      `mutation_state.py` says the same.
- [x] 5.2 `uv run scripts/check.py` passes (in the commit hook, 2026-11-27).

## Workflow follow-up

- Draft PR closing #418; act on Claude's review; mark ready; archive on the branch.
- After the merge: the delivery plan for troupe's copies of `mutation_run.py` and `mutation_state.py`; then suggest the
  owner dispatch `gh workflow run mutation.yml -R troupe-run/infrastructure -f repository=troupe` to re-score, so
  troupe#525 and #526 close if they pass.
