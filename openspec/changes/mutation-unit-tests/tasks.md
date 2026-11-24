# Tasks

## 1. Settings: a required `select`

- [ ] 1.1 Tests first (`test_mutation_settings.py`):
      - a unit's `select` loads;
      - a unit without one is refused, naming the unit and `select`;
      - empty, absolute or `..` values are refused;
      - a `deselect` outside `<tests>/<select>` is refused.
- [ ] 1.2 `mutation_settings.Unit` gains `select`, required and checked for mutmut units.
- [ ] 1.3 `scripts/mutation.json`: all eight troupe units select `unit`; troupe's three deselects go. #395's
      before-and-after test goes with them. The settings fixtures gain `select`.

## 2. The run selects only those tests

- [ ] 2.1 Tests first (`test_mutation_run.py`):
      - mutmut's test selection is `<tests>/<select>`, for the root unit and for a plugin package;
      - `do_not_mutate` and `also_copy` still cover the whole `tests` directory.
- [ ] 2.2 `mutmut_config` writes the selection.

## 3. The state resets once on a new selection

- [ ] 3.1 Tests first (`test_mutation_state.py`):
      - `save` records `select`;
      - `restore` discards a unit whose manifest has another selection, or none, as moved settings (unfit).
- [ ] 3.2 `mutation_state.save` and `restore` carry `select`.

## 4. Docs and the reseed

- [ ] 4.1 `docs/development-workflow.md`: mutation runs only each unit's selected (unit) tests, and what that shows.
      The seeding runbook covers the reseed after this change, then `gh workflow enable mutation.yml`.
- [ ] 4.2 The full check passes (in the orchestrator's slot).
