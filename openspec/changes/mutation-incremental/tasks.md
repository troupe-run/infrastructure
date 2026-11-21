# Tasks

## 1. Settings and inputs (design D5)

- [x] 1.1 Tests first: `full_refresh_days` is a whole number from 1 to 365, refused word for word otherwise; a settings
      file without it is refused
- [x] 1.2 `full_refresh_days` in `mutation_settings.py` and `mutation.json` (28)

## 2. Restoring, validating and saving state (design D2)

- [x] 2.1 Tests first, in a new `test_mutation_state.py`:
      - a unit's state is copied into `mutants/` after it's cleared, and saved back after the run, finished or not;
      - a version mismatch discards everything, a unit whose source or tests changed discards that unit, each named;
      - an unreadable `.meta` is left out alone and named, the rest carried;
      - a fill older than `full_refresh_days`, or a full-refresh request, discards on purpose, named as a refresh;
      - the unit runs with no mutant names; `--unit` runs only that unit.
- [x] 2.2 State handling (a new delivered `scripts/mutation_state.py`, which `mutation_run.py` imports)
- [x] 2.3 Tests first: `state-merge` takes the units the record says this run ran from its own state and every other
      unit, byte for byte, from the newest restored entry, merging the manifest the same way; with no newest entry it
      keeps its own (design D1a)
- [x] 2.4 `mutation_run.py state-merge`

## 3. The state record and failing visibly (design D3, D4)

- [x] 3.1 Tests first:
      - `state-<repo>.json` records, per unit, restored or not and from which run, carried and tested counts, discards
        with reasons, and saved;
      - with a previous record saying a unit was saved and no restored state for it, the unit is named lost and the
        run exits 3 after writing its report; with no previous record, a first fill exits 0;
      - the non-Python files mutmut warns about are listed as mutmut computes them (git diff from its baseline commit,
        no `.py`, its exclusion list);
      - the summary's state section, and none when there's no record.
- [x] 3.2 The record and exit in `mutation_run.py`; the summary section in `mutation_issues.py`

## 4. The workflow (design D1, D5)

- [x] 4.1 Tests first in `test_mutation_workflows.py`: the nightly cron and the schedule watch's age; the restore and
      save steps, their key and restore key, the save running on any outcome; the `unit` and `full-refresh` inputs
      reaching the run; the previous state record passed in
- [x] 4.2 `mutation.yml` and `watched-schedules.json`

## 5. Docs, the runbook and the check

- [x] 5.1 `docs/development-workflow.md`, "Mutation testing": the incremental run, what's kept and where, the blind
          spots
      and the refresh, lost state, and the seeding runbook (design D6)
- [x] 5.2 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-22)

After the apply, the seeding dispatches (design D6) fill troupe's baseline.
