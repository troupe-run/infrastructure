# Tasks

## 1. Settings and inputs (design D5)

- [ ] 1.1 Tests first: `full_refresh_days` is a whole number from 1 to 365, refused word for word otherwise; a settings
      file without it is refused
- [ ] 1.2 `full_refresh_days` in `mutation_settings.py` and `mutation.json` (28)

## 2. Restoring, validating and saving state (design D2)

- [ ] 2.1 Tests first, in a new `test_mutation_state.py`:
      - a unit's state is copied into `mutants/` after it's cleared, and saved back after the run, finished or not;
      - a version mismatch discards everything, a unit whose source or tests changed discards that unit, each named;
      - an unreadable `.meta` is left out alone and named, the rest carried;
      - a fill older than `full_refresh_days`, or a full-refresh request, discards on purpose, named as a refresh;
      - the unit runs with no mutant names; `--unit` runs only that unit.
- [ ] 2.2 State handling in `mutation_run.py`

## 3. The state record and failing visibly (design D3, D4)

- [ ] 3.1 Tests first:
      - `state-<repo>.json` records, per unit, restored or not and from which run, carried and tested counts, discards
        with reasons, and saved;
      - with a previous record saying a unit was saved and no restored state for it, the unit is named lost and the
        run exits 3 after writing its report; with no previous record, a first fill exits 0;
      - mutmut's non-Python warning is kept from its output;
      - the summary's state section, and none when there's no record.
- [ ] 3.2 The record and exit in `mutation_run.py`; the summary section in `mutation_issues.py`

## 4. The workflow (design D1, D5)

- [ ] 4.1 Tests first in `test_mutation_workflows.py`: the nightly cron and the schedule watch's age; the restore and
      save steps, their key and restore key, the save running on any outcome; the `unit` and `full-refresh` inputs
      reaching the run; the previous state record passed in
- [ ] 4.2 `mutation.yml` and `watched-schedules.json`

## 5. Docs, the runbook and the check

- [ ] 5.1 `docs/development-workflow.md`, "Mutation testing": the incremental run, what's kept and where, the blind
          spots
      and the refresh, lost state, and the seeding runbook (design D6)
- [ ] 5.2 The full check passes (in the orchestrator's slot)

After the apply, the seeding dispatches (design D6) fill troupe's baseline.
