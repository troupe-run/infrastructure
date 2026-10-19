# Spec Delta

## Purpose

Notices when a scheduled workflow the org relies on, such as website's weekly external link check, stops running,
and reports it in one tracking issue in troupe-run/infrastructure that goes on the troupe roadmap board.

## ADDED Requirements

### Requirement: The watched workflows are declared in one place
The watched workflows SHALL be declared as data in one file in this repository. Each entry SHALL name the repository,
the workflow file and the age limit in days. An entry with a missing, unknown or malformed field SHALL fail the run,
naming the entry and the field, and SHALL NOT be skipped.

#### Scenario: website's weekly check is watched
- **WHEN** the declaration is read
- **THEN** it lists `troupe-run/website`'s `.github/workflows/links-weekly.yml` with an age limit of 8 days

#### Scenario: A malformed entry
- **WHEN** an entry's age limit is not a positive whole number, or the entry has a field the declaration doesn't
  define
- **THEN** the run fails before reading GitHub, naming the entry and the field, and the tracking issue is untouched

### Requirement: The watch runs daily from infrastructure
The watch SHALL run on a daily schedule in troupe-run/infrastructure, and by hand. It SHALL NOT run on pull requests.

#### Scenario: A day passes
- **WHEN** the daily schedule fires on infrastructure's `main`
- **THEN** the watch reads every declared workflow and updates the tracking issue

#### Scenario: A pull request changes the watch
- **WHEN** a pull request changes the watch's workflow, script or declaration
- **THEN** the watch doesn't run on it, and the repository's tests check the change

### Requirement: A stopped workflow is a problem
For each declared workflow the watch SHALL find a problem when the workflow's state isn't `active`, when the
workflow isn't found, when it has never run on its schedule, or when its latest run started by the schedule began
more than its age limit ago. Runs started any other way SHALL NOT count.

#### Scenario: GitHub turned the schedule off
- **WHEN** website's `links-weekly.yml` has state `disabled_inactivity`
- **THEN** the watch reports it as a problem, with the state and the command that turns it back on

#### Scenario: The schedule is on but hasn't run
- **WHEN** the workflow is `active` and its latest scheduled run began 9 days ago
- **THEN** the watch reports it as a problem, naming when that run began

#### Scenario: Only a manual run is recent
- **WHEN** the workflow's latest run was started by hand yesterday and its latest scheduled run began 10 days ago
- **THEN** the watch reports it as a problem

#### Scenario: The workflow was renamed or deleted
- **WHEN** GitHub answers "not found" for a declared workflow
- **THEN** the watch reports it as a problem, saying the declaration needs updating

#### Scenario: All is well
- **WHEN** every declared workflow is `active` and ran on its schedule within its age limit
- **THEN** the watch finds no problem

### Requirement: An unreadable workflow is an error, not a clean result
When the watch can't read a declared workflow or its runs for any reason other than "not found", the run SHALL fail,
naming the workflow and the error, and SHALL leave the tracking issue as it is.

#### Scenario: GitHub's API fails
- **WHEN** reading a declared workflow returns a server error or a permission error
- **THEN** the run fails naming the workflow, and the tracking issue is neither opened, commented on nor closed

### Requirement: One tracking issue reports the problems
The watch SHALL keep one tracking issue in troupe-run/infrastructure, titled "Scheduled workflows stopped running"
and opened by the workflow's own token. It SHALL open the issue when it finds a problem and none is open, comment
on it only when the set of problems differs from the one last reported, and close it with a comment on the first run
that finds no problem. The issue SHALL name each problem and its fix.

#### Scenario: A first problem
- **WHEN** the watch finds a problem and no tracking issue is open
- **THEN** it opens the tracking issue, listing each problem with its fix and a link to the run

#### Scenario: The same problem the next day
- **WHEN** the watch finds the same problems the open issue last reported
- **THEN** it adds no comment

#### Scenario: The problems change
- **WHEN** the watch finds a problem the open issue hasn't reported, or one it reported is gone while another remains
- **THEN** it comments on the issue with the current problems

#### Scenario: Fixed
- **WHEN** the watch finds no problem and the tracking issue is open
- **THEN** it closes the issue with a comment linking to the clean run

#### Scenario: Two tracking issues are open
- **WHEN** more than one open issue has the tracking title and was opened by the workflow's token
- **THEN** the watch updates the oldest and says in the run's log that there are others

#### Scenario: An issue someone else opened with the same title
- **WHEN** an open issue has the tracking title but was opened by a person
- **THEN** the watch neither updates nor closes it

### Requirement: A run that finds a problem fails
A watch run that finds a problem SHALL fail after it has updated the tracking issue, so the run history shows the
problem as well as the issue.

#### Scenario: A problem is found
- **WHEN** the watch finds a problem and has opened or commented on the issue
- **THEN** the run's conclusion is failure

#### Scenario: No problem
- **WHEN** the watch finds no problem
- **THEN** the run succeeds

### Requirement: The tracking issue goes on the roadmap board
When the watch opens or comments on the tracking issue, a separate job SHALL add the issue to the troupe roadmap board
(project 1) with the board App's token from infrastructure's `board` environment. Only that job SHALL be able to read
the App's key. It SHALL check that the issue it was handed is an issue in troupe-run/infrastructure before using it.

#### Scenario: The issue is opened
- **WHEN** the watch opens the tracking issue
- **THEN** the board job adds it to project 1, and the issue's card is on the board

#### Scenario: Nothing changed
- **WHEN** the watch neither opens nor comments on the issue
- **THEN** the board job doesn't run

#### Scenario: A malformed handover
- **WHEN** the URL handed to the board job isn't of the form `https://github.com/troupe-run/infrastructure/issues/<n>`
- **THEN** the board job fails, naming the value, and adds nothing to the board

### Requirement: The issue path can be proved without stopping a watched workflow
A run started by hand SHALL accept one extra workflow to watch for that run only, named as
`troupe-run/<repository>/<workflow file>`. A value in any other form SHALL fail the run before it reads GitHub.

#### Scenario: Proving the path
- **WHEN** the owner starts the watch by hand naming a disabled scheduled workflow in a throwaway repository
- **THEN** the run reports it as a problem, opens or comments on the tracking issue, and the board job adds the issue
  to the board

#### Scenario: A value outside the org
- **WHEN** the extra workflow names a repository outside troupe-run, or isn't in the documented form
- **THEN** the run fails naming the value, and the tracking issue is untouched

### Requirement: Outside GitHub Actions the watch only reports
Run outside GitHub Actions, the watch SHALL print each declared workflow's result and what it would do to the tracking
issue, and SHALL NOT open, comment on or close any issue.

#### Scenario: Run locally
- **WHEN** the owner runs the watch on their own machine
- **THEN** it prints each workflow's result and the action it would take, and changes nothing on GitHub
