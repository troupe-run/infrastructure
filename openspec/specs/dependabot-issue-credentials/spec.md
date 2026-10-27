# dependabot-issue-credentials Specification

## Purpose

Declares the credential infrastructure's `dependabot-issues` workflow uses to open an issue for each Dependabot pull
request and link the pull request to it: the `troupe-run-dependabot` App's installation, the main-only environment in
infrastructure that holds its key, and the variable that names the App.

## Requirements

### Requirement: The Dependabot issues App is narrow
The App `troupe-run-dependabot` SHALL have only these repository permissions: issues read/write, pull requests
read/write, and metadata read. It SHALL have no organisation permission. Its installation SHALL select repositories
and SHALL cover troupe, website and infrastructure. Its permissions and repository selection SHALL be checked by the
drift check, and its repository list by hand (spec: teams-and-access).

#### Scenario: The App gains a permission
- **WHEN** the App's installation gains a permission on GitHub, such as contents write, without the declaration
  changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The App is switched to all repositories
- **WHEN** the App's installation is changed to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The App gains a repository
- **WHEN** a repository other than troupe, website and infrastructure, such as `.github`, is added to the App's
  installation
- **THEN** the next hand check of its repository list, made by any change that depends on it, finds it, and it's
  removed or the declaration is changed in a pull request

#### Scenario: The declared App matches
- **WHEN** the App has exactly the declared permissions and repository selection
- **THEN** the drift check reports no difference for it

### Requirement: The App's token can't change code or merge
A token minted for the App SHALL be able to open, edit, comment on, close and reopen issues, and edit a pull request's
description, in the three repositories. It SHALL NOT be able to push to any branch, merge a pull request, or change a
workflow, a ruleset or a setting.

#### Scenario: Merging with the App's token
- **WHEN** a run tries to merge a Dependabot pull request with the App's token
- **THEN** GitHub refuses it, for want of contents write

#### Scenario: Pushing with the App's token
- **WHEN** a run tries to push a commit to any branch in troupe, website or infrastructure with the App's token
- **THEN** GitHub refuses it

### Requirement: The App's key is readable from infrastructure's main only
troupe-run/infrastructure SHALL have an environment named `dependabot-issues` whose deployment branches are limited to
`main`, and which no admin can bypass. The App's private key SHALL be held only as that environment's secret
`DEPENDABOT_APP_PRIVATE_KEY`, so a run on any other branch, or in another repository, can't read it.

#### Scenario: A run on another branch asks for the environment
- **WHEN** a workflow run on a branch other than `main` in infrastructure uses the `dependabot-issues` environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from it

#### Scenario: The branch policy is changed by hand
- **WHEN** someone widens the environment's deployment branches, or allows admins to bypass them, on GitHub
- **THEN** the next plan shows the change being reverted

#### Scenario: Removing or weakening the declaration fails the check
- **WHEN** a change deletes the environment's declaration, lets it deploy from a branch other than `main`, or lets
  admins bypass it
- **THEN** `scripts/check.py` fails, naming the repository, the environment and what changed, before any plan is made

### Requirement: The App's key never passes through this repository
OpenTofu SHALL NOT hold or set the value of `DEPENDABOT_APP_PRIVATE_KEY`. The owner SHALL set it from the password
manager with a documented command that prints nothing. Checking that it's set SHALL read its name only.

#### Scenario: The key is set
- **WHEN** the owner has run the documented command
- **THEN** listing the `dependabot-issues` environment's secrets shows `DEPENDABOT_APP_PRIVATE_KEY` by name, and no
  value appears in the repository, the state, a plan or a log

#### Scenario: A plan runs
- **WHEN** a plan runs with these declarations in place
- **THEN** it neither creates, changes nor deletes `DEPENDABOT_APP_PRIVATE_KEY`

### Requirement: The App's client ID is declared as a repository variable
troupe-run/infrastructure SHALL have the repository variable `DEPENDABOT_APP_CLIENT_ID`, holding the App's client ID,
declared once in this repository. A different value on GitHub, or the variable's removal, SHALL show in the next plan.

#### Scenario: The variable is changed by hand
- **WHEN** someone changes `DEPENDABOT_APP_CLIENT_ID` on GitHub
- **THEN** the next plan shows it changing back to the declared client ID

#### Scenario: The variable is deleted by hand
- **WHEN** someone deletes `DEPENDABOT_APP_CLIENT_ID`
- **THEN** the next plan shows it being created with the declared client ID

### Requirement: The App bypasses no ruleset
The App SHALL NOT be a bypass actor on any ruleset. It writes nothing to a repository's contents.

#### Scenario: The rulesets after the change
- **WHEN** a plan runs with these declarations in place
- **THEN** no ruleset's bypass actors change
