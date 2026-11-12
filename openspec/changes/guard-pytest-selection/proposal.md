# Proposal

## Why

`guard_pytest` fails tests that pass when tests from several packages are selected by node id
(`a/tests/test_a.py::test_x b/tests/test_b.py::test_y`). It blames each test for the *other* selected modules'
collection reads: their source, their `__pycache__/*.pyc`, and the temporary `.pyc.<n>` written beside it (#298,
reported in troupe as troupe-run/troupe#365). It isn't about xdist. On troupe's `theatre-template-and-guard-xdist`
branch the issue's command gives 2 passed, 2 errors in one process, and 3 passed, 2 errors with `-n 2`.

The cause is how pytest collects a node id. `Session.collect` walks each argument's parts and collects every module
it needs *inside* the Session's own collect report (pytest 9.2.0, `_pytest/main.py`, the `matchparts` loop calling
`_collect_one_node`). The guard opens a read window for each collector's report, and a read joins every open window.
So the Session's window (node id `""`) holds every selected module's imports. Every test's `listchain()` includes the
Session, so every test is charged with all of them. A run given paths, or no arguments, collects modules after the
Session's report has closed, which is why full runs and per-package runs are clean.

Running a few tests by node id is what an agent does to check its work, and troupe's #365 can't close until the
guard it's delivered stops reporting reads that never happened. `guard_pytest` is written here and delivered to
troupe, so this is where it's fixed.

## What Changes

- **A read made while a collector is being collected counts for that collector only**, the innermost one whose report
  is open, not the collectors it's nested in. Test and fixture windows don't change: a read in them still joins every
  open window. A test still gets its own module's reads and its own collectors', so a module-level
  `TEXT = DOC.read_text()` or a parametrize built from a file still counts for every test in that module.
- **Full runs and runs given paths don't change.** In them no collector's report is made inside another's, so
  "innermost only" and "every open one" record the same reads.
- **Tests** in `scripts/tests/test_guard_pytest.py` select tests from two scopes by node id, with and without xdist:
  a clean selection passes, and an untagged read in it still fails that one test only. A module-level read in a node-id
  selection still counts for its own module's tests.
- **Delivered to troupe and website** in the usual way, once CI is green on all three OSes and the owner approves the
  plan. troupe's pull request #385 then adds troupe's own test on top and closes troupe-run/troupe#365.

Not changing: the tag rule (`guard.tag_violations`), the messages, how fixtures' and tests' own reads are recorded,
Hypothesis's exclusion, and the fact that reads in subprocesses aren't seen.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: adds a requirement that a read made while collecting a module or other collector counts
  only for the tests under that collector, whichever way the tests were selected (paths, node ids, or none; with or
  without xdist). It's an ADDED requirement rather than a scenario on "Test tags cover what each test reads", which
  would push that requirement's text past the 500-character limit `openspec validate --strict` enforces.

## Impact

- `scripts/guard_pytest.py` (`_record`, `pytest_make_collect_report`, and the docstrings that say what counts as a
  read) and `scripts/tests/test_guard_pytest.py`.
- The delivered copies in troupe-run/troupe and troupe-run/website (an apply after merge).
- Unblocks troupe-run/troupe#365 (troupe PR #385).
