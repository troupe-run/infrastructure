## REMOVED Requirements

### Requirement: Mutation testing runs weekly from infrastructure
**Reason**: the scheduled run is now nightly and incremental (#378); "Mutation testing runs nightly from infrastructure" replaces it.
**Migration**: none: the workflow, its dispatch and its exclusion from pull requests stay as they were; only the schedule moves from weekly to nightly.

## ADDED Requirements

### Requirement: Mutation testing runs nightly from infrastructure
A workflow in troupe-run/infrastructure SHALL run mutation testing nightly, and on demand, over each repository the list
names (the requirement on naming them in one place), each at its `main`, on Linux with Python 3.15. This scheduled
workflow SHALL NOT run on pull requests or merge groups. No mutation testing SHALL be a required check, so none blocks a
merge. The scheduled workflow SHALL be one of the scheduled workflows the schedule watch declares.

#### Scenario: The scheduled run
- **WHEN** the nightly schedule fires and the list names only troupe
- **THEN** the workflow mutates and tests troupe at its `main`, and no other repository

#### Scenario: A pull request
- **WHEN** a pull request is opened, or enters the merge queue, in any repository
- **THEN** the scheduled workflow doesn't run, and no required check waits for any mutation testing (a listed
  repository's ready pull request gets the report of its own changes instead)

#### Scenario: One repository on demand
- **WHEN** the owner dispatches the workflow naming one listed repository
- **THEN** only that repository is mutated, and its modules' issues are kept as on a scheduled run

#### Scenario: A repository the list doesn't name, on demand
- **WHEN** the owner dispatches the workflow naming website, which the list doesn't name
- **THEN** the run fails before mutating anything, naming website and the repositories the list names

### Requirement: The scheduled run resumes from the last run's state
The scheduled run SHALL keep mutmut's results between runs and resume from them: each unit SHALL run with no mutant
names, so results stored for unchanged functions stand and only the rest are tested, and a run SHALL save its state
whether or not it finished. A run started right after another SHALL restore the state that run saved. The summary SHALL
say, per unit, how many results were carried and how many tested in this run.

#### Scenario: Filling the baseline
- **WHEN** the owner dispatches the run three times back to back and the budget stops the first two
- **THEN** each run continues where the last stopped, and none re-tests a result the last one saved

#### Scenario: A night with a small change
- **WHEN** one function changed since the last run
- **THEN** that function's mutants are tested again, the others' results are carried, and the summary says how many of
  each

### Requirement: Lost or unfit state is named and fails visibly
A run SHALL record the state it saved. When a unit's state the previous run saved can't be restored, or restored state
doesn't fit (another mutmut version, or the unit's sources or tests changed in the settings), the run SHALL start that
unit afresh, name it and why, and fail visibly. A file of state that can't be read SHALL discard only that source file's
results, named. A first fill with no state saved before SHALL NOT fail.

#### Scenario: An evicted cache
- **WHEN** the previous run saved troupe's state and this run's restore finds none
- **THEN** troupe's unit starts afresh, the summary says its saved state is gone, and the run fails

#### Scenario: One unreadable file
- **WHEN** one source file's results in the restored state can't be read
- **THEN** that file's mutants are tested again and named, the rest are carried, and the run fails visibly

#### Scenario: The first fill
- **WHEN** no previous run saved any state
- **THEN** every unit starts empty, the summary says it's a first fill, and the run doesn't fail for it

### Requirement: A full refresh clears what incremental runs can't see
The settings SHALL give `full_refresh_days`; when a unit's state was first filled longer ago than that, or the owner
dispatches a full refresh, the run SHALL discard the state on purpose and say so. mutmut's warning about non-Python
files changed since the last full run SHALL be named in the summary.

#### Scenario: The refresh falls due
- **WHEN** troupe's state was first filled 29 days ago and `full_refresh_days` is 28
- **THEN** the run discards it, says it's a scheduled refresh, and refills; modules not yet reached aren't judged

#### Scenario: A dependency bump
- **WHEN** `uv.lock` changed since the last full run
- **THEN** cached results stay, and the summary names `uv.lock` among the non-Python files mutmut warned about
