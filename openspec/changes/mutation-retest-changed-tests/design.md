# Design

## Context

See proposal.md, "Why". What mutmut 3.8.1 does with kept state, from its source:

- `create_file_mutants` re-mutates a source file and keeps `exit_code_by_key` for every function whose hash (its own
  code) is unchanged; a changed or new function's results become `null`.
- `collect_or_load_stats` loads `mutmut-stats.json` (`tests_by_mangled_function_name`, `duration_by_test`,
  `function_hashes`, ...). It lists the tests, drops names that no longer exist, and runs stats only for tests not in
  `duration_by_test` ("new tests"), adding what they reach. It resets no result: only a changed test selection, test
  arguments or (opt-in) non-Python files reset results, and test files are Python.
- The tests a mutant runs are exactly `tests_by_mangled_function_name[<its function>]`; mutmut runs only mutants whose
  result is `null`.
- A test name is pytest's node id from mutmut's working directory, such as `tests/unit/test_cli.py::test_x[1]`.

troupe's unit tests import shared helpers from `packages/troupe/tests/` by module name (`runtesting`, `storetesting`,
`protocol_schemas`), and those helpers change often (`runtesting.py` 6 times in 2.5 weeks of November).

## Goals / Non-Goals

**Goals:**

- A result kept from an earlier night is re-tested when a test change could change it.
- Nights with no test change cost what they cost now.

**Non-Goals:**

- Re-testing a function's callers when the function changes (mutmut's other blind spot). The full refresh still
  covers it.
- Changing the pull request report: it keeps no state.
- Changing mutmut. It's a pinned upstream tool; the scripts stay standard library only.

## Decisions

### D1. A fingerprint of the unit's tests, kept in the manifest

Each unit's manifest entry gains `tests_fingerprint`: for every file under the unit's `tests` (the whole directory,
not only `select`, since helpers live beside it), its path relative to `tests` and a SHA-256 of its content.
`__pycache__` and `.pyc` are left out. Comparing the restored fingerprint with the checkout's gives the added, edited
and removed files.

*Alternative:* `git diff` against the commit the state was saved at. The workflow's checkout is shallow, and content
hashes need no history.

### D2. The tests a change names

From the changed files:

- a changed or removed test file (`test_*.py` or `*_test.py`) names itself;
- a changed or removed Python helper names every test file that imports it, directly or through other helpers under
  `tests` (read with `ast`: `import x`, `from x import ...`, `from . import x`, matched to `x.py` or `x/__init__.py`
  by module name under `tests`);
- a changed `conftest.py` names every test file under its directory;
- a changed file that isn't Python names every test file.

A named test file names every test in mutmut's kept stats whose node id is in that file. The node id's file part is
mapped to the checkout as `deselected` maps the other way (`src/<tests>` for a root unit, the path from the working
directory for a package's unit).

*Alternative:* discard the unit's state whenever a test file changes. That's correct but throws the speed-up away on
most nights, and a troupe refill took one whole 4-hour budget without finishing (24,118 of 24,871 mutants). With
helpers changing every few days, the tail would never be reached.

### D3. Before the run: clear what the named tests reached, and forget what they reached

For each function whose kept tests include a named test, every result is set to `null` in its `.meta`, killed ones
too: a killing test that changed or went may no longer kill. The named tests are removed from
`tests_by_mangled_function_name` and `duration_by_test`, so mutmut takes them as new and collects what they reach
now. Done in `restore`, after the files are copied.

### D4. After the run: clear what gained a test, and run once more

mutmut collects new tests' stats before it runs any mutant, so a mutant it tests in this run already uses them. Only
carried results miss them. After the run, the stats are compared with those kept (after D3): a function that gained a
test, whose hash is unchanged and which still holds results decided before the run, has those results set to `null`.

If any were cleared, mutmut exited 0 and the budget isn't spent, `mutmut run` runs once more: it regenerates nothing
new, loads the stats, runs the clean tests and tests only the cleared mutants. Otherwise the cleared results are saved
as they are and the next night tests them. One more pass is enough: the second run adds no test.

This also covers state whose stats can't be read: mutmut then collects every test's stats, every function gains its
tests, and every carried result is cleared.

### D5. State without a fingerprint counts every test as changed

The first night after this change, every unit's state lacks `tests_fingerprint`, so every test file counts as changed
and the summary names it ("no record of the unit's tests: every test counts as changed"). It re-tests what the tests
reach, once, much like a full refresh but without failing the run: the state fits, it's just older.

### D6. Named in the record and the summary

`UnitState` gains `tests_changed` (the changed paths, relative to `tests`), `cleared_for_tests` (results cleared by D3
and D4) and `retested` (whether the second pass ran). The summary's state section gives the count and the first few
paths per unit, and says when the budget left cleared results for the next night.

## Risks / Trade-offs

- [A helper reached other than by import (a fixture file read by path, a subprocess)] → a non-Python change names
  every test; Python run as a child is integration-only (unit tests start no processes, #507); the full refresh
  remains.
- [A node id form the mapping doesn't expect] → the tests are built from node ids mutmut 3.8.1 wrote in the
  reproduction, and the apply's container trial runs the whole path against real mutmut. A file whose tests D2
  named but which matches no kept test names is printed, so a mismatch shows in the log.
- [The second pass costs a clean run of the unit's tests] → only on nights when tests changed; minutes against a
  4-hour budget.
- [The first night re-tests nearly everything] → once, and it's what #525/#526 need anyway.

## Migration Plan

Merge, then the delivery plan for troupe's copies (the pull request report imports `mutation_state.py`, unchanged in
behaviour there). Then the owner dispatches `gh workflow run mutation.yml -R troupe-run/infrastructure -f
repository=troupe`; D5 makes it re-test the `troupe.cli` modules. No full refresh is needed. Rollback is a revert:
older code ignores `tests_fingerprint`.
