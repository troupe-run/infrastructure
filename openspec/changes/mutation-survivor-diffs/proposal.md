# Proposal

## Why

A mutation run that uses its whole budget couldn't write its report once survivors passed about 4,500 (#404). Reseed
run 2 after #394 was cancelled by the job's 270-minute timeout in the report phase. After mutmut stops, `run_mutmut`
rendered each survivor's diff with its own `mutmut show <name>` process, at about 0.35 s each. Unit-only runs leave
far more survivors, since code that only integration tests reach now survives, which is the honest signal. Decided by
the orchestrator (2026-11-25): option A.

## What Changes

- A new delivered script, `scripts/mutation_show.py`, prints exactly what `mutmut show` prints for many mutants in one
  process. It calls mutmut's own `get_diff_for_mutant` and `status_by_exit_code`, run by mutmut's own interpreter in
  mutmut's working directory. What goes is the per-mutant work `mutmut show` repeats: starting Python and importing
  mutmut, and walking every `.meta` file to find the mutant.
- `mutation_report.to_show` lists, file by file, the mutants `from_mutmut` reads diffs for, by the same rules.
  `run_mutmut` renders them all with one run of `mutation_show.py`, through `mutation_run.shown`. A render that fails,
  isn't JSON, or leaves a mutant out is an error, never a blank diff.
- `mutation_locator_check.py` gains `show-equal`, the proof that the output equals real `mutmut show`, as #377's
  locator check proves the locator. It runs in a throwaway container, in a unit's mutmut working directory:
  - mutmut generates the mutants as text;
  - the survivors a CI run's report names are marked as survived in the `.meta` files;
  - every one is compared.
  No mutant runs, and no result is produced locally. It joins the checks to re-run on a mutmut upgrade.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a run's report renders its survivors' diffs in one process, the same as `mutmut show`.

## Impact

- `scripts/mutation_show.py` (new), `scripts/mutation_run.py` and `scripts/mutation_report.py`, all delivered to
  troupe: `tofu/guard_delivery.tf`'s `mutation_report_files` and `scripts/guard_tests_needed.py` gain the new file.
- `scripts/mutation_locator_check.py` (not delivered), and the tests: `test_mutation_show.py`, and `fake_show` in
  `test_mutation_run.py`.
- The plan adds troupe's `scripts/mutation_show.py` and updates its `mutation_run.py` and `mutation_report.py`.
