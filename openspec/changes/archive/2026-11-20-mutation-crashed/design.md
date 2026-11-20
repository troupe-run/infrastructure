# Design

## Context

`mutation_report.py` (report version 1) has a `Survivor` record and a module's `survivors` list, which the reader holds
to the `survived` count. Crashes are only counted. mutmut 3.8.1's `exit_code_by_key` maps `-9`/`-11` (and the like) to
"crashed". Stryker 10.1.1's status `RuntimeError` maps to "crashed", with no exit code. The reports are made and read
in the same run (weekly: mutate, then issues; per PR: mutate, then comment), so no report outlives the code that
reads it.

## Decisions

### D1. A `Crashed` record, and version 2

`Crashed(name, path, line, change, exit_code: int | None)`, a module's `crashed_mutants: tuple[Crashed, ...]`, and in
JSON a `crashed_mutants` list on each module, required and held to `crashed` exactly as `survivors` is to `survived`.
The schema is closed, so the report's `VERSION` becomes 2. A version 1 report is refused, naming the version. Both
sides of every report are this code, so nothing older has to be read.

### D2. Collected where survivors are

- `from_mutmut`: for a "crashed" status, the same `function_start`/`mutated_line` over `mutmut show`, and the code.
- `from_stryker`: for `RuntimeError`, the same line and replacement as a survivor, with `exit_code` None.
- `mutation_run.run_mutmut` maps crashed paths from `src/…` back to the unit's source, as it does survivors'.

The per-PR report (`mutation_pr.py`'s own schema) reports survivors on changed lines and is unchanged: the owner's
question is about the weekly run.

### D3. The summary says what each ended

After the module table, `summary()` lists every crashed mutant, one line each, shaped as an issue's survivor line:
`` - `troupe.core.x_f__mutmut_3` at `packages/troupe/src/troupe/core/x.py:42` (exit -9): `-old / +new` ``, or
"(no exit code)" for Stryker. The name, path and change go through `code()`, since they come from a run of other code.
The list sits under one line that says what they ended: "Crashed mutants: each ended only its own test process, and
the tool recorded it and went on. Excluding any (`# pragma: no mutate`) is the owner's decision." A crash that ends
the run never reaches the report: the step's `::error::` says how the run ended (#345 D3).

### D4. The step keeps the host's account of how it ended

Dry run 44633465646 ended with SIGTERM to the step's own shell (exit 143): `run_contained`'s message never printed, and
nothing inside the run's namespace can signal that shell. Free memory had fallen 4.7 GB in the last minute. The readings
couldn't say who sent it. So the sampler's exit trap now also runs `sudo -n journalctl --since <step start>` and keeps
only the lines from the sources that can name who ended a run: the kernel's OOM lines, systemd-oomd, and systemd's lines
on the runner's service or this run's `mutation-*` scope. Other units stopping (timers, mounts) and words that merely
contain "oom" are left out, so they can't push the line that matters past the 200-line cap (review of #362). At most 200
lines go to the log (`journal: …`) and to `out/journal-<repository>.log`, which uploads with the readings (the pull
request report's `journal-pr.log` too). With none, or no readable journal, it saves nothing. `sudo -n` fails quietly
where sudo can't run. The orchestrator folded this into #361 (2026-11-20): it's the same diagnostic purpose, in the same
steps.

## Risks / Trade-offs

- **Many crashes make a long summary** → it's a dry-run and weekly summary for the owner to read once. Issues still
  list survivors only.

## Migration Plan

Merge and apply (troupe's `mutation_report.py` and `mutation_run.py`), then the troupe dry run, whose summary names
the crashed mutants for the owner.
