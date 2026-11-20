# Proposal

## Why

Troupe's dry run 44661743047 ended at mutant 2,410 of 19,615. A single mutmut test process grew to 5.2 GB of
resident memory in under a minute, which pushed the run's 12G cgroup (`MemoryMax`, #345) past its limit. The kernel's
OOM killer killed it, and systemd then stopped the whole run. Dry run 44633465646 ended the same way at the same
point. That run's cgroup is the only memory limit, and mutmut's per-mutant timeout can't catch a process that eats
gigabytes this fast. So one runaway mutant ends the run, no report is written, and #361's crashed-mutant list never
names it (infrastructure#366).

## What Changes

- **Each mutant's test process gets a memory cap.** It's set by a new `mutant_memory_mb` setting in
  `scripts/mutation.json`, where null means no cap. The mutmut plugin (`scripts/mutation_children.py`) applies it with
  `RLIMIT_AS`, only in a process that tests a mutant. A runaway then raises `MemoryError` or dies on its own. mutmut
  records it (killed or crashed) and goes on, and #361's list names it for the owner's exclusion decision.
- **The run measures what the cap must allow.** For each unit, the run logs a `memory:` line with the peak virtual
  size (`VmPeak`) and peak resident size (`VmHWM`) of:
  - mutmut's own process, where the stats and clean passes run and from which every mutant's process is forked;
  - the largest mutant processes.

  The cap limits virtual size, not resident memory. A forked mutant's process also starts at mutmut's own size. So
  the default comes from these measured peaks, not from dividing 12G (orchestrator, 2026-11-20).
- **The setting starts null.** It's set from a measured troupe run, and that run's clean pass must stay under it.
  How that measurement reaches CI is the owner's open choice (design D4).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a runaway mutant ends only its own test process, and a run records the memory its passes peak
  at.

## Impact

- `scripts/mutation.json`, `scripts/mutation_settings.py`, `scripts/mutation_run.py` and
  `scripts/mutation_children.py` (all delivered to troupe), and their tests.
- `docs/development-workflow.md`, "Mutation testing".
- The plan updates troupe's delivered copies of those four files.
- Not changed: the run's own cgroup (`MemoryMax` 12G, #345), which stays as the backstop.
