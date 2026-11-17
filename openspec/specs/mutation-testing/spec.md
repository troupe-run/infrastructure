# mutation-testing Specification

## Purpose
Mutation testing of troupe, infrastructure and website, which reports and never blocks a merge. A weekly run keeps one
`test-quality` issue on the roadmap board for each module whose score is under the threshold or below its recorded
baseline, which only moves up, and names the pull request that added each new surviving mutant. On each ready pull
request, a report mutates the changed code and comments with the survivors on its changed lines and the run's time.
Every number they judge by is declared in one settings file.

## Requirements

### Requirement: Mutation testing runs weekly from infrastructure
A workflow in troupe-run/infrastructure SHALL run mutation testing weekly, and on demand, over troupe's and
infrastructure's Python and website's TypeScript, each at its `main`, on Linux with Python 3.15. This weekly workflow
SHALL NOT run on pull requests or merge groups. No mutation testing SHALL be a required check, so none blocks a merge.
The weekly workflow SHALL be one of the scheduled workflows the schedule watch declares.

#### Scenario: The weekly run
- **WHEN** the weekly schedule fires
- **THEN** the workflow mutates and tests troupe, infrastructure and website at their `main`, each in its own job

#### Scenario: A pull request
- **WHEN** a pull request is opened, or enters the merge queue, in any repository
- **THEN** the weekly workflow doesn't run, and no required check waits for any mutation testing (a ready pull request
  gets the report of its own changes instead)

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
The score threshold, the ratchet's tolerance, the time budgets, the fewest mutants a module needs to be judged, the
most new issues one run may open per repository, the tool versions, and what each repository mutates and tests SHALL
be declared in one file in infrastructure. Every job SHALL read them from
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

### Requirement: Each module under the threshold or its baseline has exactly one issue
For each module judged under the threshold or below its baseline, the run SHALL keep exactly one open issue in the
module's repository,
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
- **WHEN** a module with an open issue scores at or over both the threshold and its baseline
- **THEN** the issue gets a comment with the new score and is closed as completed

#### Scenario: A module falls again after its issue closed
- **WHEN** a module whose issue was closed falls under the threshold or its baseline again
- **THEN** a new issue is opened; the closed one stays closed

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
A run SHALL open at most the declared number of issues per repository. Modules beyond that SHALL be named
in the run's summary and handled by a later run. Open issues SHALL always be updated or closed.

#### Scenario: More modules than the cap
- **WHEN** eight modules in troupe fall under the threshold and the cap is 5, with none having an issue
- **THEN** five issues are opened, the summary names the other three, and the next run opens issues for those still
  under

### Requirement: New issues go on the roadmap board
Every issue the run opens SHALL be added to the troupe roadmap board, by the board's own credential, in a
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

### Requirement: A module's baseline only moves up
Each repository's committed quality-gates file SHALL hold, in its mutation table, each judged module's baseline score.
A module SHALL count as having fallen when its score is below its baseline by more than the declared tolerance. A run
SHALL report every baseline it would raise, to max(baseline, score), in its summary and the module's issue, and SHALL
NOT write or lower one: a baseline changes only through an ordinary pull request.

#### Scenario: A module falls below its baseline
- **WHEN** a module with a 72.0% baseline scores 70.5%, above the 60% threshold, with a tolerance of 0
- **THEN** its issue is opened or updated, saying it fell below its 72.0% baseline

#### Scenario: A module improves
- **WHEN** a module with a 72.0% baseline scores 75.0%
- **THEN** the run reports the baseline it would raise to 75.0%, and no issue is opened

#### Scenario: A module with no baseline
- **WHEN** a module with no recorded baseline is judged at 64.0%
- **THEN** no issue is opened, and the run reports 64.0% as the baseline to record

### Requirement: A malformed mutation table is an error
A malformed mutation table SHALL fail the run for that repository, naming the file and the key, and SHALL NOT be read
as having no baselines.

#### Scenario: A malformed baseline
- **WHEN** a repository's mutation table gives a module a score of "high"
- **THEN** that repository's issues are left alone, and the run fails naming the file, the module and the key

### Requirement: New survivors are attributed to the pull request that added them
The weekly run SHALL call a surviving mutant new when the line it mutates was last changed by a commit that isn't in the
previous weekly run's tested commit for that repository. The module's issue SHALL list new survivors first, each naming
the commit and the merged pull request that contains it, so GitHub cross-references the issue on that pull request.
With no previous run to compare with, no survivor SHALL be called new.

#### Scenario: A pull request adds an untested branch
- **WHEN** a pull request merged since the last weekly run adds a line whose mutant survives
- **THEN** the module's issue lists that survivor under new survivors, naming the pull request, and the pull request's
  timeline shows the issue mentioning it

#### Scenario: An old survivor
- **WHEN** a survivor's line was last changed before the previous weekly run's tested commit
- **THEN** it's listed with the other survivors, with no pull request named

#### Scenario: The first run
- **WHEN** no previous weekly run's report is available
- **THEN** no survivor is called new

### Requirement: Each ready pull request's changed code is mutation tested, as a report
On every pull request that's ready for review in troupe, website and infrastructure, a workflow delivered from
infrastructure SHALL mutate the code the pull request changed and report the surviving mutants on changed lines, in one
comment on the pull request, edited in place on later pushes, and in the run's summary, with its runtime. It SHALL NOT
be a required check, and SHALL conclude success when it finds survivors. Only its own failure to run SHALL fail it.

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

### Requirement: The job that runs a pull request's code holds no write token
In the pull request workflow, the job that runs the pull request's code under mutation SHALL have a read-only token,
and SHALL hand on only a report. The job that comments SHALL check out only the pull request's base commit, never its
head, and SHALL read the report as data against a closed schema.

#### Scenario: A malformed pull request report
- **WHEN** the comment job reads a report with a field the schema doesn't name
- **THEN** it writes no comment and fails, naming the field
