## ADDED Requirements

### Requirement: Mutation testing runs weekly from infrastructure
A workflow in troupe-run/infrastructure SHALL run mutation testing weekly, and on demand, over troupe's and
infrastructure's Python and website's TypeScript, each at its `main`, on Linux with Python 3.15. It SHALL NOT run on
pull requests or merge groups, and SHALL NOT be a required check, so it never blocks a merge. The workflow SHALL be
one of the scheduled workflows the schedule watch declares.

#### Scenario: The weekly run
- **WHEN** the weekly schedule fires
- **THEN** the workflow mutates and tests troupe, infrastructure and website at their `main`, each in its own job

#### Scenario: A pull request
- **WHEN** a pull request is opened, or enters the merge queue, in any repository
- **THEN** no mutation testing runs, and no required check waits for it

#### Scenario: One repository on demand
- **WHEN** the owner dispatches the workflow naming one repository
- **THEN** only that repository is mutated, and its modules' issues are kept as on a weekly run

### Requirement: The jobs that run tests hold no secret
A job that runs a repository's code or tests under mutation SHALL have a read-only token and no environment, and
SHALL hand on only a report. The job that writes issues SHALL run no repository's tests, SHALL read each report as data
against a closed schema, and SHALL treat a missing or malformed report as an error naming the repository.

#### Scenario: A malformed report
- **WHEN** a repository's report has a field the schema doesn't name, or lacks one it requires
- **THEN** that repository's issues are left alone, the others are handled, and the run fails naming the repository and
  the field

#### Scenario: A repository's job failed
- **WHEN** the job for one repository fails or times out before writing its report
- **THEN** the other repositories' issues are handled, that repository's are left alone, and the run fails naming it

### Requirement: Mutation testing's settings are declared once
The score threshold, the time budget per repository, the fewest mutants a module needs to be judged, the most new
issues one run may open per repository, the window in which a closed issue is reopened, the tool versions, and what
each repository mutates and tests SHALL be declared in one file in infrastructure. Every job SHALL read them from
there. An unknown or malformed setting SHALL fail the check.

#### Scenario: The threshold moves
- **WHEN** a pull request changes the threshold in the settings file
- **THEN** the next run judges every module by the new threshold, and nothing else needs to change

#### Scenario: A misspelt setting
- **WHEN** the settings file has a key it doesn't declare, or a threshold outside 0 to 100
- **THEN** `scripts/check.py` fails, naming the file, the key and what's valid

#### Scenario: The job timeout follows the budget
- **WHEN** the budget changes and the workflow's job timeout doesn't
- **THEN** this repository's tests fail, naming both

### Requirement: A module's score counts untested code against it
A module's mutation score SHALL be the mutants caught (killed, timed out or crashed) as a percentage of the mutants
caught, survived or not covered by any test. Skipped mutants SHALL NOT count. A module SHALL be judged only when it has
at least the declared fewest mutants and the run finished all of its mutants within the budget.

#### Scenario: A module with an untested function
- **WHEN** a module has 20 mutants, of which 10 are killed, 4 survive and 6 are in a function no test calls
- **THEN** its score is 50%

#### Scenario: A small module
- **WHEN** a module has fewer mutants than the declared floor
- **THEN** it's listed in the run's summary as not judged, and no issue is opened, updated or closed for it

#### Scenario: The budget runs out
- **WHEN** a repository's budget runs out before all of a module's mutants have run
- **THEN** that module is listed in the summary as not finished and isn't judged, and the modules that finished are
  judged as usual

### Requirement: Each module under the threshold has exactly one issue
For each module judged under the threshold, the run SHALL keep exactly one open issue in the module's repository,
labelled `test-quality`. The run SHALL recognise its own issue by a marker naming the repository and module, in an
issue its credential opened, and SHALL never open a second one for the same module.

#### Scenario: A module falls under the threshold
- **WHEN** a module scores under the threshold and has no issue from the run
- **THEN** an issue is opened in its repository, labelled `test-quality`, listing its surviving mutants

#### Scenario: A module stays under the threshold
- **WHEN** a module with an open issue scores under the threshold again
- **THEN** that issue's description is rewritten with this run's numbers and survivors, no other issue is opened, and
  a comment is added only if the score or the number of survivors changed

#### Scenario: A module recovers
- **WHEN** a module with an open issue scores at or over the threshold
- **THEN** the issue gets a comment with the new score and is closed as completed

#### Scenario: A module falls back under soon after
- **WHEN** a module scores under the threshold and its issue was closed within the declared reopen window
- **THEN** that issue is reopened and updated rather than a new one opened

#### Scenario: A person's issue quotes the marker
- **WHEN** an issue opened by a person contains a module's marker
- **THEN** the run doesn't edit or close it, and keeps its own issue for the module

#### Scenario: Two runs at once
- **WHEN** a dispatched run starts while another is in progress
- **THEN** it waits for the other to finish, so neither opens an issue the other opened

### Requirement: A module's issue lists its surviving mutants
A module's issue SHALL name the module, its score, the threshold, its mutant counts and the run. It SHALL list the
surviving mutants, each with its location and change: the first 30, then how many more and how to list them all.

#### Scenario: A module with 45 survivors
- **WHEN** a module under the threshold has 45 surviving mutants
- **THEN** its issue lists 30 of them with location and change, says 15 more survive, and names the command or report
  that lists them all

### Requirement: A run opens a bounded number of new issues
A run SHALL open, or reopen, at most the declared number of issues per repository. Modules beyond that SHALL be named
in the run's summary and handled by a later run. Open issues SHALL always be updated or closed.

#### Scenario: More modules than the cap
- **WHEN** eight modules in troupe fall under the threshold and the cap is 5, with none having an issue
- **THEN** five issues are opened, the summary names the other three, and the next run opens issues for those still
  under

### Requirement: New issues go on the roadmap board
Every issue the run opens or reopens SHALL be added to the troupe roadmap board, by the board's own credential, in a
job that only adds issues whose URL is an issue in troupe, infrastructure or website.

#### Scenario: A new issue
- **WHEN** the run opens an issue
- **THEN** it's on the troupe roadmap board when the run finishes

#### Scenario: An unexpected URL
- **WHEN** the board job is handed something that isn't an issue URL in one of the three repositories
- **THEN** it adds nothing and fails, naming what it was handed

### Requirement: A dry run only reports
A run dispatched as a dry run, and any run outside GitHub Actions, SHALL write no issue, comment or board item. It
SHALL report every module's score and what it would open, update, reopen or close.

#### Scenario: The calibration run
- **WHEN** the owner dispatches the workflow as a dry run
- **THEN** the run's summary lists each module's score and the issues it would open, and no issue changes
