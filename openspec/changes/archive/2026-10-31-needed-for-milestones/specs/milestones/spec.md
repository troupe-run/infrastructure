## ADDED Requirements

### Requirement: A plan that closes a milestone lists the open issues with no milestone
When a plan changes a declared milestone from open to closed, the plan's comment on a pull request and the plan of
`main` shown for approval SHALL list every open issue with no milestone in each listed repository that has issues,
with its repository, number, title and link, and how many there are. A plan that closes no milestone SHALL list
nothing. The list SHALL NOT fail or block the plan by its length.

#### Scenario: A pull request closes a release
- **WHEN** a pull request sets `0.1.0`'s declared state to `closed` and its plan runs, while troupe has four open
  issues with no milestone and website has none
- **THEN** the plan's comment says `0.1.0` closes, lists troupe's four issues, says website and infrastructure have
  none, and says each one needs an outcome before the merge

#### Scenario: The plan of main
- **WHEN** that pull request merges and the plan of `main` runs
- **THEN** the run summary the owner approves from shows the same list, as it is at that moment

#### Scenario: A plan that closes nothing
- **WHEN** a pull request re-describes a milestone, or changes no milestone
- **THEN** its plan comment has no list of issues with no milestone

#### Scenario: A repository with issues off
- **WHEN** a plan closes a milestone, and `.github`, a listed repository, has issues turned off
- **THEN** the list leaves `.github` out and says why

#### Scenario: A pull request isn't an issue
- **WHEN** a listed repository has an open pull request with no milestone
- **THEN** the list leaves it out

### Requirement: The list of issues with no milestone is never silently short
When the issues of a listed repository can't be read, the step that makes the list SHALL fail, naming the repository,
and SHALL NOT show the list as if that repository had none. Every page of a repository's issues SHALL be read.

#### Scenario: A repository can't be read
- **WHEN** a plan closes a milestone and reading troupe's issues fails
- **THEN** the step fails naming troupe, and no comment says troupe has no issues with no milestone

#### Scenario: More than one page of issues
- **WHEN** a repository has 150 open issues with no milestone
- **THEN** the list shows all 150
