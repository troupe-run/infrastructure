# teams-and-access Specification

## Purpose

Declares who and what has access to the org's repositories. It starts with the GitHub Apps installed in the org (what
each may do and how its repositories are chosen); teams join it when the org has some.

## Requirements

### Requirement: Each App's installation is declared and checked
For each GitHub App installed in the org (today DCO, `troupe-run-infrastructure`, `troupe-run-release` and
`troupe-run-board`), its permissions and its repository selection (all repositories, or selected ones) SHALL be
declared here. A difference from GitHub SHALL be reported by a drift check that only reads. The check SHALL run in CI
whenever `main` is planned, daily included (spec: ci-apply), as well as by hand.

#### Scenario: An App given a new permission is reported
- **WHEN** an App's installation gains a permission on GitHub without the declaration changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: An App switched to all repositories is reported
- **WHEN** an App's installation is changed from selected repositories to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The declared installations match
- **WHEN** each App's permissions and repository selection match the declaration
- **THEN** the drift check reports no difference

#### Scenario: A permission granted by hand is caught within a day
- **WHEN** an owner grants an App a new permission on GitHub, and nobody runs the check by hand
- **THEN** the next daily run of `main`'s plan fails its drift job, naming the App and the permission

### Requirement: Each App's repositories are listed and confirmed by hand
The repositories each App is installed on SHALL be listed in this repository. GitHub doesn't let any token this repo
holds read that list, so the list SHALL say so, and SHALL be confirmed by hand in the App's settings by any change
that adds, removes or depends on a repository.

#### Scenario: A change adding a managed repository confirms the App covers it
- **WHEN** a change brings a new repository under management
- **THEN** its tasks include adding the repository to the infrastructure App's installation and updating the list, and
  the plan reads the repository's real settings rather than its public view

### Requirement: No App is installed that nothing uses
Each App installed in the org SHALL be used by something this repository declares or documents. An App that nothing
uses SHALL be deleted, and its declaration and its keys removed with it.

#### Scenario: The declared installations are only the ones in use
- **WHEN** the drift check reads the org's App installations
- **THEN** it finds exactly DCO, `troupe-run-infrastructure` and `troupe-run-release`, and reports no difference

#### Scenario: The release App is used
- **WHEN** someone asks what uses `troupe-run-release`
- **THEN** this repository names troupe's release workflow (troupe-run/troupe#23) and the `release` environment and
  variable it declares for it (spec: release-credentials)
