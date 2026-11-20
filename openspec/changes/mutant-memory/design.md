## Context

The weekly run contains mutmut in a PID namespace and a cgroup capped at 12G (#345). It reaps orphans (#347), names
crashed mutants (#361), and keeps the host's journal lines on how a run ended (#361 D4). Dry run 44661743047 used that
journal to show a single mutmut test process at 5.2 GB anonymous RSS ("mutmut: troupe.") taking the cgroup to its
limit. The kernel killed it, and systemd failed the scope (`oom-kill`), so the whole run ended at mutant 2,410 of
19,615. Memory had held at ~14 GB free until the last minute.

How mutmut 3.8.1 runs, which this design relies on (and #341's per-mutant `setsid` already depends on):
- the stats pass, the clean run and test listing run in mutmut's own process;
- each mutant's tests run in a process forked from it, which calls pytest, so the plugin's `pytest_configure` runs
  there with `MUTANT_UNDER_TEST` naming the mutant.

A forked process starts with mutmut's address space, at whatever size mutmut has reached by then.

## Goals / Non-Goals

**Goals:**
- A runaway mutant ends only its own test process, is recorded, and (if crashed) is named by #361's list.
- The cap is set from measured peaks, with the clean pass shown to fit under it.
- The cap is one setting, null by default, changed in one place.

**Non-Goals:**
- Excluding any mutant. That's the owner's decision, from #361's list.
- Changing the run's own cgroup (12G), which stays as the backstop.
- Stryker (website isn't listed for mutation).

## Decisions

### D1. `RLIMIT_AS` in each mutant's process, set by the plugin

`scripts/mutation_children.py`'s `pytest_configure` already starts a session in each mutant's process (#341). It now
also calls `resource.setrlimit(RLIMIT_AS, (cap, cap))` there, and only there, where `MUTANT_UNDER_TEST` holds
`__mutmut_`. A runaway then gets `MemoryError` (its test fails, so the mutant is killed) or dies (crashed, and named).
Processes its tests start inherit the cap, each with its own address space.

Mutant processes only, because the stats and clean passes run in mutmut's own process. Capping that process would cap
mutmut itself, and every fork after it.

Alternative, kept in reserve: a per-mutant cgroup. The orchestrator suggested `systemd-run --scope -p MemoryMax`
inside the contained run. mutmut forks its children itself, so there's no command to wrap. The plugin would need to
move each child into a delegated sub-cgroup, which needs root, or cgroup delegation set up for the run's scope. That
caps resident memory, which is what actually ran out, so it is the fallback if D4's measurement shows `RLIMIT_AS`
tripping ordinary mutants.

### D2. The cap reaches the plugin in a file beside it

`run_mutmut` already copies the plugin into mutmut's working directory. It now also writes
`_mutation_children_plugin.json` beside it, containing `{"mutant_memory_mb": n | null, "peaks": "<path>"}`. The plugin
reads it through its own `__file__`. An environment variable would reach every process the tests start, and the tests
of the guard's own environment handling would see it. A missing file means no cap, as before, so the plugin still
works when loaded by hand. A file that is there but malformed is an error naming the file.

### D3. Each process records its peaks, and the run logs the largest

`pytest_unconfigure` in every process the plugin loads in appends one line to the `peaks` file:
`<MUTANT_UNDER_TEST or "mutmut"> <VmPeak kB> <VmHWM kB>`, read from `/proc/self/status`. The line is short and the
file is opened with `O_APPEND`, so concurrent children don't interleave. After each unit's run, `mutation_run` logs:
- `memory: <unit> mutmut VmPeak=… MB VmHWM=… MB`, the largest over mutmut's own passes;
- the five largest mutant processes, by `VmPeak`, with their names;
- how many processes recorded.

These lines go in the job's log, which both the weekly and the pull request run keep. A process the kernel kills
writes nothing; a capped runaway that gets `MemoryError` does, at about the cap. With no `/proc` (macOS, tests),
nothing is recorded and the run says so.

### D4. The default comes from measurement, and starts null

The cap's starting value is null, so nothing changes until a measured value is set. The value is then the larger of
mutmut's own `VmPeak` and the largest `VmPeak` of an ordinary mutant (one that didn't run away), with room to spare
(half as much again), rounded up to 256 MB. It's recorded in the settings with the run that measured it.

The clean pass is shown to fit by its measured peak being under the cap. The run under the cap is shown not to trip
ordinary mutants by its killed/survived rate matching the uncapped run's over the same mutants. Dry run 44661743047
gives the comparison: 1,734 killed and 480 survived of its first 2,410. Many ordinary mutants killed by `MemoryError`
would mean `RLIMIT_AS` is too blunt, which is D1's fallback.

How the measurement reaches CI is the owner's choice:
- **(A) Two pull requests.** This one with the setting null, and a dry run after its apply. Then one that sets the
  value.
- **(B) One.** A dry run dispatched from this branch. That route isn't documented, so it needs the owner's agreement
  and a documentation issue.

## Risks / Trade-offs

- `RLIMIT_AS` counts reserved address space. Threads (8 MB stacks each), mmap'd files and allocator arenas can reach
  it well below the resident size that matters → mitigated by setting the cap from measured `VmPeak` with margin, and
  by D4's check against the uncapped run's rates.
- A runaway that allocates in C without checking can segfault rather than raise → it's then crashed and named by
  #361's list. That's the outcome wanted.
- A `MemoryError` caught by the code under test could leave a mutant surviving where it would have been killed.
  Rare, and visible in the survivors.
- Two capped children plus mutmut can still exceed 12G resident in principle → the run's cgroup stays as the
  backstop, and the journal names that case (#361 D4).
