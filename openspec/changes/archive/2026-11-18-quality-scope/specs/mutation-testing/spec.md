## MODIFIED Requirements

### Requirement: Mutation testing runs weekly from infrastructure
A workflow in troupe-run/infrastructure SHALL run mutation testing weekly, and on demand, over each repository the list
names (the requirement on naming them in one place), each at its `main`, on Linux with Python 3.15. This weekly workflow SHALL NOT run on pull requests or merge groups. No
mutation testing SHALL be a required check, so none blocks a merge. The weekly workflow SHALL be one of the scheduled
workflows the schedule watch declares.

#### Scenario: The weekly run
- **WHEN** the weekly schedule fires and the list names only troupe
- **THEN** the workflow mutates and tests troupe at its `main`, and no other repository

#### Scenario: A pull request
- **WHEN** a pull request is opened, or enters the merge queue, in any repository
- **THEN** the weekly workflow doesn't run, and no required check waits for any mutation testing (a listed repository's
  ready pull request gets the report of its own changes instead)

#### Scenario: One repository on demand
- **WHEN** the owner dispatches the workflow naming one listed repository
- **THEN** only that repository is mutated, and its modules' issues are kept as on a weekly run

#### Scenario: A repository the list doesn't name, on demand
- **WHEN** the owner dispatches the workflow naming website, which the list doesn't name
- **THEN** the run fails before mutating anything, naming website and the repositories the list names

### Requirement: Each ready pull request's changed code is mutation tested, as a report
On every pull request that's ready for review in each repository the list names that receives the guard's files, a
workflow delivered from infrastructure SHALL mutate the code the pull request changed and report the surviving mutants on changed lines, in one
comment on the pull request, edited in place on later pushes, and in the run's summary, with its runtime. It SHALL NOT
be a required check, and SHALL conclude success when it finds survivors. Only its own failure to run SHALL fail it.

#### Scenario: A repository the list doesn't name
- **WHEN** a ready pull request in infrastructure, which holds the report's workflow as its source but isn't on the
  list, is tested
- **THEN** the report mutates nothing and runs no tests, says the repository isn't on the list, and doesn't fail

#### Scenario: A branch made before a delivery
- **WHEN** a ready pull request's branch was made before infrastructure delivered the report's scripts to its
  repository
- **THEN** the report runs on the pull request's merge with its base, which has them, and mutates only the lines the
  pull request changed

#### Scenario: A pull request leaves a changed line untested
- **WHEN** a ready pull request changes a function, and a mutant on a changed line survives
- **THEN** the pull request's mutation comment lists it with its location and change, the job succeeds, and the merge
  isn't held

#### Scenario: An exempted line
- **WHEN** a changed line carries the tool's exemption with a reason
- **THEN** no mutant on it is reported

#### Scenario: Unchanged code isn't reported
- **WHEN** a mutant survives on a line the pull request didn't change
- **THEN** it isn't in the comment

#### Scenario: Another push
- **WHEN** the pull request is pushed to again
- **THEN** the same comment is edited with the new result, and no second comment appears

#### Scenario: A draft
- **WHEN** a draft pull request is opened or pushed to
- **THEN** no mutation runs

#### Scenario: No source changed
- **WHEN** a ready pull request changes no file the repository's targets mutate
- **THEN** nothing is mutated, and the comment, if one exists, says so

#### Scenario: The runtime is recorded
- **WHEN** the run finishes, or stops at its budget
- **THEN** its comment and its report give the time of each step and of the whole job

## ADDED Requirements

### Requirement: The repositories that get coverage and mutation testing are named in one place
One list in troupe-run/infrastructure SHALL name the repositories that get coverage and mutation testing: the weekly
mutation run, the pull request mutation report, and a coverage gate. The weekly run's jobs, and which repositories
receive the pull request report, SHALL follow it and nothing else. Infrastructure's own check SHALL measure coverage
only when the list names infrastructure. Adding a repository SHALL take one pull request to the list.

#### Scenario: The list today
- **WHEN** the list names only troupe
- **THEN** the weekly run mutates troupe alone, only troupe receives the pull request report, and infrastructure's own
  check measures no coverage

#### Scenario: A repository is taken off the list
- **WHEN** a pull request removes website from the list, and website held the delivered pull request report
- **THEN** the plan deletes the report's workflow and scripts from website, and website's delivered file list no
  longer names them

#### Scenario: Infrastructure's coverage follows the list
- **WHEN** infrastructure's `quality-gates.toml` declares `[coverage]` while the list doesn't name infrastructure
- **THEN** this repository's tests fail, naming the table and the list

### Requirement: A repository's mutation run finds the files its tests read
A mutation run SHALL let a repository's tests find the files they read beside their source, wherever the tool's copy
puts them, and SHALL keep the repository's own pytest options apart from those that can't work in the copy. A test that
can't run under the tool at all SHALL be deselected in the settings, with its reason.

#### Scenario: troupe's tests find the repository's files
- **WHEN** troupe's `troupe` package is mutated and a test reads `plugins/runner-anthropic/fixtures`, counting
  directories up from its own file
- **THEN** it finds the directory, as it does outside the run

#### Scenario: troupe's own pytest plugins load
- **WHEN** troupe's package is mutated
- **THEN** its tests run with the plugins troupe's pytest options load, without `--strict-markers` and the guard's tag
  plugin, which can't find their declarations from the copy
