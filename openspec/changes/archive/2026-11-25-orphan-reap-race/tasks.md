# Tasks

## 1. Fix the poll (#407)

- [x] 1.1 Add tests that `exec` the poll's read with a stubbed `open`: one raising `ProcessLookupError` and one
  returning an empty read each report gone (`None`). A `stat` line gives its state letter, and a line with no `)`
  raises. Run them against the current read first. Verify the two gone tests fail without the fix: the
  `ProcessLookupError` one with that error escaping, and the empty-read one with an `IndexError`.
  Done: against the old read, 3 failed (`ProcessLookupError` escaped; `IndexError` for the empty read and for the
  line with no `)`), and the state-letter test passed.
- [x] 1.2 Move the read into `STATE_OF` (`state_of(pid)`), make `ORPHAN` use it, and treat `FileNotFoundError`,
  `ProcessLookupError` and an empty read as gone. Verify the 1.1 tests pass, and `uv run scripts/check.py` passes
  under ruff 0.17.5 and under ruff 0.17.6 (`uvx ruff@0.17.6 check .` and `uvx ruff@0.17.6 format --check .`).
  Done: the module's tests pass (52 passed, 9 skipped: the contained ones need Linux, so CI runs them); both ruff
  versions report all checks passed and 142 files formatted.
- [x] 1.3 Open a draft pull request with `Closes #407`, using `--body-file`, and act on Claude's review. Verify the
  review of the last push completed with no must-fix or decision open, and CI's check passes, the contained test
  included.
  Done: #408. Claude's review of 27877ae had no findings. CI's check passed on 27877ae: 4064 passed, none skipped,
  so the contained orphan test ran.
