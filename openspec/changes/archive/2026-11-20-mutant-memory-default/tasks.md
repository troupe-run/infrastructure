# Tasks

## 1. The cap (design D1)

- [x] 1.1 Test first in `test_mutation_settings.py`: the declared settings load with `mutant_memory_mb` 2048, with a
      comment naming the measurement (dry run 44693481824)
- [x] 1.2 `scripts/mutation.json` sets `"mutant_memory_mb": 2048`

## 2. The record and the check

- [x] 2.1 `docs/development-workflow.md`, "Mutation testing": the cap's value, the measured peaks and the run they came
      from, replacing "null until a measured run sets it"
- [x] 2.2 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-20)

After the apply, the proving troupe dry run checks design D2's two conditions. They're reported with numbers to the
orchestrator. If ordinary mutants die of `MemoryError`, stop and raise the cgroup fallback.
