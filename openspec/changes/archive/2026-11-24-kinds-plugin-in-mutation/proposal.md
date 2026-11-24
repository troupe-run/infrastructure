# Proposal

## Why

troupe's mutation runs fail before mutating anything (#398). Both the scheduled run and a pull request's report are
affected. troupe#510 added the pytest plugin `kinds_pytest` to troupe's `addopts`. It reads each test's kind from its
path relative to the repository. Inside mutmut's copy (`packages/<package>/mutants/tests/unit/…`), that path is under
no suite, so the plugin refuses every test, and mutmut's stats pass fails. The first reseed after #394 stopped after
about 30 seconds: "kinds: tests/unit/test_anthropic_host_unit.py is in neither kind's directory".

## What Changes

- `scripts/mutation_run.py` leaves `kinds_pytest` out of the repository's `addopts` in mutmut's copy, as it already does
  for the guard's tag plugin and `--strict-markers` (`UNHONOURED_PLUGINS`).
- Mutation selects the unit tests by directory since #394, so it needs no kinds there. The plugin's in-process check
  still guards troupe's own suite, which troupe's CI runs with it.
- The spec scenario that names which of troupe's options a run leaves out adds the kinds plugin, and the development
  workflow says the same.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: the run leaves troupe's kinds plugin out of mutmut's copy too.

## Impact

- `scripts/mutation_run.py` (delivered to troupe), with its test, and `docs/development-workflow.md`.
- The plan updates troupe's delivered `scripts/mutation_run.py`.
