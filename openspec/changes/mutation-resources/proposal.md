# Proposal

## Why

troupe's weekly mutation run doesn't finish. Two dry runs for troupe alone, after #332, both lost their hosted runner
while mutmut was mutating, well inside the 240-minute budget:

- 44280076869: "The runner has received a shutdown signal", 27 minutes into the job;
- 44284687854: "The hosted runner lost communication with the server … starves it for CPU/Memory", 82 minutes into
  the Mutate step. No job log was kept.

`scripts/mutation_run.py` runs mutmut with `max_children = 4` on a 4-CPU runner, each child running troupe's tests.
Nothing records the runner's memory, swap or disk, so the cause isn't proven. Separately, troupe's entry in
`scripts/mutation.json` lists only its eight packages: none of the six runner plugins under `plugins/` (about 12,100
lines of source) is mutated, and no design says why. It's a gap (#337).

## What Changes

- **A run records its resources.** The weekly and pull request mutate jobs sample memory, swap, disk and load every
  minute while mutmut runs, to the job's log and to a file uploaded with the report, so a lost runner leaves what it
  last saw.
- **`max_children` is a setting** in `scripts/mutation.json`, read strictly like the others (a whole number from 1 to
  the runner's 4 CPUs), set to 2. Both runs use it.
- **A package's unit copies its package's own files.** As a root unit already copies the checkout's top-level entries,
  a package's unit copies its package directory's (a plugin's `tools/`, for example), so tests that find them from
  their own file still do inside mutmut's copy.
- **troupe's runner plugins come next**, in #339 (blocked by #337): a second change adds them as six more units once a
  dry run of troupe's packages, with this change applied, finishes within the budget (design D4). #337 was narrowed to
  this change so its pull request can close it (owner, 2026-11-19).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: `max_children` joins the declared settings; a run records the resources it uses; a package's
  unit copies its own files.

## Impact

- `scripts/mutation.json`, `scripts/mutation_settings.py`, `scripts/mutation_run.py`, a small sampler (in
  `scripts/mutation_run.py` or a step in the workflows), `.github/workflows/mutation.yml`, `.github/workflows/mutation-pr.yml`,
  their tests, the docs' "Mutation testing" section.
- Delivered to troupe: `mutation-pr.yml`, `mutation.json`, `mutation_run.py`, `mutation_settings.py` change, so the
  apply updates them there.
- Dry runs happen in CI only (owner, 2026-11-18): no local mutation load.
