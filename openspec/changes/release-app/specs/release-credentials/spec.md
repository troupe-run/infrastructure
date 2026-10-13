# Spec Delta

## Purpose

Declares the credential troupe's release workflow uses to open release pull requests, and where it may be read: the
release App's installation, the `release` environment that holds its key, and the variable that names the App.

## ADDED Requirements

### Requirement: The release App is narrow and installed on troupe only
The release App `troupe-run-release` SHALL have only these repository permissions: contents, pull requests and issues
read/write, and metadata read. It SHALL have no organisation permissions. Its installation SHALL select repositories,
and SHALL cover `troupe-run/troupe` only. Any difference SHALL be reported by the drift check or the hand-confirmed
list (spec: teams-and-access).

#### Scenario: The release App gains a permission
- **WHEN** the release App's installation gains a permission on GitHub, such as administration, without the
  declaration changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The release App is switched to all repositories
- **WHEN** the release App's installation is changed to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The declared release App matches
- **WHEN** the release App has exactly the declared permissions and selected repositories
- **THEN** the drift check reports no difference for it

### Requirement: The release key is readable from main only
troupe SHALL have an environment named `release` whose deployment branches are limited to `main`, and which no
admin can bypass. The App's private key SHALL be held only as that environment's secret `RELEASE_APP_PRIVATE_KEY`, so
a workflow run on any other branch can't read it.

#### Scenario: A run on another branch asks for the environment
- **WHEN** a workflow run on a branch other than `main` uses the `release` environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from it

#### Scenario: The branch policy is changed by hand
- **WHEN** someone widens the `release` environment's deployment branches, or allows admins to bypass them, on GitHub
- **THEN** the next plan shows the change being reverted

### Requirement: The release key's value never passes through this repository
OpenTofu SHALL NOT hold or set the value of `RELEASE_APP_PRIVATE_KEY`. The owner SHALL set it from the password
manager with a documented command that prints nothing. Checking that it's set SHALL read its name only.

#### Scenario: The key is set
- **WHEN** the owner has run the documented command
- **THEN** listing the `release` environment's secrets on troupe shows `RELEASE_APP_PRIVATE_KEY` by name, and no
  value appears in the repository, the state, a plan or a log

#### Scenario: A plan runs
- **WHEN** a plan runs with the release declarations in place
- **THEN** it neither creates, changes nor deletes `RELEASE_APP_PRIVATE_KEY`

### Requirement: The release App's client ID is declared as a repository variable
troupe SHALL have the repository variable `RELEASE_APP_CLIENT_ID`, holding the release App's client ID, declared in
this repository. A different value on GitHub, or the variable's removal, SHALL show in the next plan.

#### Scenario: The variable is changed by hand
- **WHEN** someone changes `RELEASE_APP_CLIENT_ID` on troupe on GitHub
- **THEN** the next plan shows it changing back to the declared client ID

#### Scenario: The variable is deleted by hand
- **WHEN** someone deletes `RELEASE_APP_CLIENT_ID` from troupe
- **THEN** the next plan shows it being created with the declared client ID

### Requirement: The release App never bypasses protect main
The release App SHALL NOT be a bypass actor on any ruleset. Its changes SHALL reach troupe's `main` only through a
pull request that passes troupe's required checks.

#### Scenario: troupe's ruleset after the change
- **WHEN** a plan runs with the release declarations in place
- **THEN** troupe's "protect main" ruleset's bypass actors are unchanged: the org admins on pull requests, and the
  infrastructure App
