# Design

## Context

See proposal.md. What's there now (2026-11-18, after #332/#334):

- `scripts/mutation_run.py` writes mutmut's `setup.cfg` with `max_children=4` (`CHILDREN`), for every unit of every
  run, weekly and pull request. The runner is GitHub's `ubuntu-latest` (4 CPUs, 16 GB for a public repository).
- In both troupe dry runs, the stats pass and the clean run of troupe's suite completed (about 12 minutes), then the
  runner was lost while mutants ran: once after 15 minutes of mutation, once after about 70. The second kept no job
  log at all (`BlobNotFound`), so evidence that only goes to the log can vanish.
- troupe's plugins (`plugins/runner-*`) have the packages' layout (`src/`, `tests/`, plus their own `tools/` or
  `fixtures/`). A test in `runner-anthropic` reads `Path(__file__).resolve().parents[1] / "tools" / ...`: inside
  mutmut's copy (`<plugin>/mutants/tests`), `parents[1]` is `<plugin>/mutants`, which has no `tools/`.

## Goals / Non-Goals

**Goals:** troupe's weekly run finishes and reports every module; a lost runner leaves evidence; the plugins are
mutated.

**Non-Goals:** a larger or self-hosted runner (a cost decision for the owner, if this isn't enough); changing what
counts towards a module's score.

## Decisions

### D1. Resources are sampled from the start of the Mutate step, to the log and to a file

A background loop, started at the beginning of the Mutate step and stopped at its end, prints one line a minute: the
time, `MemAvailable`, `SwapFree` (from `/proc/meminfo`), the free space on the workspace's disk, the 1-minute load,
and the number of mutmut processes. Each line goes to the job's log (live, so whatever GitHub kept shows the last
readings) and is appended to `out/resources-<repository>.log`, which the existing upload step carries (it runs on any
outcome but cancelled). A runner that's lost takes the file with it, so the log is the evidence then, and the file is
the record otherwise. The sampler is a few lines of shell in the step, not Python: it must keep running when Python's
processes are what starves the runner. The summary line ("lowest MemAvailable: … at …") is printed when the step ends.

*Alternative:* mutmut's own output. It doesn't report resources, and its progress line is a spinner.

### D2. `max_children` is a setting, 2 to start

`scripts/mutation.json` gains `"max_children": 2`, required and read strictly: a whole number from 1 to 4 (the
runner's CPUs; more would only oversubscribe). `mutation_run.mutmut_config` reads it from the settings instead of
`CHILDREN`. Both runs use it: the pull request report runs on the same runner type. Halving it roughly doubles the
mutation phase's time; the first troupe dry run measures that against the 240-minute budget (D4).

### D3. A package's unit copies its package's other top-level entries

`mutmut_config`, for a unit whose source is a package's `src` (mutmut runs in the package directory), adds the
package directory's other top-level entries to `also_copy`, except `src`, the tests, `mutants`, `setup.cfg`, the
plugin copy, hidden entries (caches, `.venv`) and build output (`dist`, `build`, `*.egg-info`). The package's
`pyproject.toml` and any `uv.lock` are copied on purpose: they're its own files, and mutmut already copies
`pyproject.toml` itself. troupe's packages gain their `LICENSE`,
`README.md` and `CHANGELOG.md` in the copy (harmless); the plugins gain `tools/` and `fixtures/`, which their tests read.

### D4. The plugins come after a successful dry run of the packages

Order of work: D1-D3, merge and apply, then a dry run for troupe. If it finishes within the budget, the six plugins
are added as units in a second pull request, under #339, and a second dry run checks them. Splitting it this way keeps a run that
still fails readable: one change at a time.

If the packages alone don't fit the budget at 2 children, or the plugins push it over, the fallback is to split
troupe across matrix jobs, each with its own budget (packages, plugins), which needs a `unit` dimension in the
weekly matrix. That would be its own change, proposed with the measurements.

## Risks / Trade-offs

- **2 children may still starve the runner** → D1's readings say which resource ran out; 1 child is the next step,
  and a larger runner the last, which is the owner's decision.
- **Half the parallelism doubles the mutation time** → the dry run measures it; D4's fallback covers a run that
  doesn't fit.

## Migration Plan

1. Merge; the apply delivers the changed files to troupe.
2. Dispatch `mutation.yml` as a dry run for troupe; report the scores, the runtime and the lowest free memory.
3. If it fits: add the plugins (second pull request), and dry-run again.
