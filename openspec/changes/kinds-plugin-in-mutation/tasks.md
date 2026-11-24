# Tasks

## 1. Leave the kinds plugin out of mutmut's copy

- [x] 1.1 Test first (`test_mutation_run.py`): troupe's `kinds_pytest` (`-p kinds_pytest` and `-pkinds_pytest`) is left
      out of the `addopts` the run gives mutmut, and troupe's other plugins stay
- [x] 1.2 `UNHONOURED_PLUGINS` gains `kinds_pytest`
- [x] 1.3 `docs/development-workflow.md` names the kinds plugin with the options a run leaves out
- [x] 1.4 A container trial of mutmut's stats pass and clean tests (no mutant runs) over troupe's eight units at troupe
      main, with this branch's scripts: each unit's selected tests collect and pass in the copy, or the failure is
      named and explained (results on #398)
- [x] 1.5 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-24)
