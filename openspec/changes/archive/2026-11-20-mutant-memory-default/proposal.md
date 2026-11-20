# Proposal

## Why

#366: a runaway mutant takes the troupe run's 12G cgroup to an OOM kill and ends the whole run. All three
uncapped dry runs ended this way, at mutant 2,410-2,493 of 19,615. #367 (#368) built a per-mutant memory cap with the
setting null. #371 (#372) made its measurement survive the kill. The measuring dry run 44693481824 has now recorded
the peaks the cap is set from (design D4 of `2026-11-20-mutant-memory`):

| Process | VmPeak (virtual) | VmHWM (resident) |
|---|---|---|
| mutmut's own (stats and clean passes) | 1,111 MB | 553 MB |
| largest ordinary mutant (`troupe.cli.render.x__changes__mutmut_28`) | 1,270 MB | 453 MB |
| the runaway (killed by the kernel, so unrecorded; from the journal) | 5,289 MB | 4,481 MB |

2,299 processes recorded.

## What Changes

- **`mutant_memory_mb` is 2,048.** The rule is the larger measured `VmPeak` (1,270 MB) plus half (1,905 MB), rounded
  up to 256 MB. That leaves 778 MB over the largest ordinary mutant and stops the runaway at under half its virtual
  size. Two capped mutants plus mutmut stay far under the 12G cgroup resident.
- **The measurement is recorded** in the design and docs, with the run it came from, so the next change to the cap
  can compare.
- The proof comes after the apply. The next troupe dry run under the cap must (a) get past mutant ~2,410-2,493 and
  (b) keep the killed/survived rate over its first 2,410 mutants near 44661743047's 1,734 killed / 480 survived. If
  ordinary mutants die of `MemoryError`, `RLIMIT_AS` is too blunt, and the per-mutant cgroup fallback goes to the
  owner.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: the per-mutant cap is set, from a recorded measurement.

## Impact

- `scripts/mutation.json` (delivered to troupe) and `scripts/tests/test_mutation_settings.py`.
- `docs/development-workflow.md`, "Mutation testing".
- The plan updates troupe's delivered `scripts/mutation.json`, nothing else.
