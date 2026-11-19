# Tasks

Built while website#136 waits, with targeted test runs only; the full check and commits wait for the orchestrator's
slot (2026-11-18). Dry runs are in CI only.

## 1. max_children as a setting (design D2)

- [x] 1.1 Tests first in `test_mutation_settings.py`: `max_children` is required, a whole number from 1 to 4, and a
      wrong value is refused naming it; the fixture settings gain it too
- [x] 1.2 `scripts/mutation_settings.py` reads it; `scripts/mutation.json` sets 2; `mutation_run.mutmut_config` writes
      `max_children` from the settings (tests: the config carries the setting's value, not a constant)

## 2. A package's unit copies its package's files (design D3)

- [x] 2.1 Tests first in `test_mutation_run.py`: a package unit's config lists the package's other top-level entries
      in `also_copy`, without `src`, the tests, `mutants`, `setup.cfg`, the plugin copy and `.venv`
- [x] 2.2 Change `mutmut_config`

## 3. Resource readings (design D1)

- [x] 3.1 The Mutate step of `mutation.yml` and the mutate step of `mutation-pr.yml` start a sampler that writes one
      line a minute to the log and to `out/resources-<repository>.log`, stop it when mutmut ends, and print the lowest
      `MemAvailable` seen
- [x] 3.2 Tests: run the sampler's shell with a fake `/proc/meminfo` and a short interval, check the line's fields and
      that it stops; the upload step still carries `out/`

## 4. Docs and verification

- [x] 4.1 `docs/development-workflow.md`'s "Mutation testing": `max_children`, the readings, what a package's unit
      copies
- [ ] 4.2 The full check passes (when the orchestrator gives the slot); the pull request's plan updates troupe's four
      delivered files and nothing else

## Workflow follow-up

- After the merge and apply: dispatch `mutation.yml` as a dry run for troupe; report the scores, the runtime against
  the budget, and the lowest free memory.
- If it fits: #339's change adds the six runner plugins as units, then another dry run (design D4).
