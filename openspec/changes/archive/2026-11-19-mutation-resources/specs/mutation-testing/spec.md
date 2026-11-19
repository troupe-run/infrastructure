## MODIFIED Requirements

### Requirement: Mutation testing's settings are declared once
The score threshold, the ratchet's tolerance, the time budgets, how many mutants run at once, the fewest mutants a
module needs to be judged, the most new issues one run may open per repository, the tool versions, and what each
repository mutates and tests SHALL be declared in one file in infrastructure. Every job SHALL read them from there. An
unknown or malformed setting SHALL fail the check.

#### Scenario: The threshold moves
- **WHEN** a pull request changes the threshold in the settings file
- **THEN** the next run judges every module by the new threshold, and nothing else needs to change

#### Scenario: A misspelt setting
- **WHEN** the settings file has a key it doesn't declare, or a threshold outside 0 to 100
- **THEN** `scripts/check.py` fails, naming the file, the key and what's valid

#### Scenario: The job timeout follows the budget
- **WHEN** the budget changes and the workflow's job timeout doesn't
- **THEN** this repository's tests fail, naming both

#### Scenario: Fewer mutants at once
- **WHEN** the settings say 2 mutants run at once
- **THEN** the weekly run and the pull request report each run mutmut with at most 2 children

## ADDED Requirements

### Requirement: A mutation run records the resources it uses
While a weekly or pull request mutation run mutates, its job SHALL record the runner's memory, swap, disk and load at
least once a minute, both in the job's log and in a file uploaded with the run's report, so a run whose runner is lost
still leaves what it last recorded.

#### Scenario: The runner is lost
- **WHEN** the runner stops responding while mutmut runs
- **THEN** the job's log, as far as it was kept, shows the readings up to then, each with its time

#### Scenario: The run finishes
- **WHEN** a run finishes
- **THEN** its uploaded report includes the readings file, and the run's summary gives the lowest free memory seen

### Requirement: A package's unit has its package's own files
When a unit's source is a package's `src`, its mutation run SHALL copy the package directory's other top-level entries
into mutmut's copy, as a unit at the repository's root copies the checkout's, so a test that finds them from its own
file finds them there too.

#### Scenario: A plugin's tools
- **WHEN** a test in `plugins/runner-anthropic/tests` reads `tools/capture_anthropic.py` from its package, counting
  one directory up from its own file
- **THEN** it finds the file inside mutmut's copy, as it does outside the run
