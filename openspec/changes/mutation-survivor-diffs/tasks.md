# Tasks

## 1. The render

- [x] 1.1 Tests first (`test_mutation_show.py`):
      - `to_show` lists survivors and crashed mutants file by file, never the tests';
      - one render by the interpreter beside `mutmut`, with nothing started when there's nothing to show;
      - a failed render, non-JSON output, a non-object, a mutant left out, or a missing interpreter is an error;
      - the script refuses a malformed request.
- [x] 1.2 `scripts/mutation_show.py`, `mutation_report.to_show`, and `mutation_run.shown` wired into `run_mutmut`.
      `fake_show` stands in for the one render.
- [x] 1.3 `mutation_show.py` is delivered: `tofu/guard_delivery.tf` and `scripts/guard_tests_needed.py`.

## 2. The proof

- [x] 2.1 Tests first: `show-equal` reads the survivors a CI report names, by mutmut's paths, for one unit.
- [x] 2.2 `mutation_locator_check.py show-equal`, and its docstring's mutmut-upgrade checklist.
- [x] 2.3 A container run of `show-equal` over troupe's eight units at reseed run 3's commit (47778e6), with that
      run's report. No mutant runs. Every survivor is equal, with results posted on #404.

## 3. Check

- [x] 3.1 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-25).
