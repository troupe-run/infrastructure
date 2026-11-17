# mutation-issue-credentials Specification

## Purpose
Declares the credential infrastructure's weekly mutation run uses to keep its test-quality issues in troupe, website and
infrastructure: the `troupe-run-test-quality` App's installation, which can write issues and nothing else, the
main-only `mutation-issues` environment in infrastructure that holds its key, and the variable that names the App.

## Requirements

### Requirement: The test-quality App is narrow
The App `troupe-run-test-quality` SHALL have only these repository permissions: issues read/write and metadata read.
It SHALL have no organisation permission. Its installation SHALL select repositories and SHALL cover troupe, website
and infrastructure. Its permissions and repository selection SHALL be checked by the drift check, and its repository
list by hand (spec: teams-and-access).

#### Scenario: The App gains a permission
- **WHEN** the App's installation gains a permission on GitHub, such as pull requests write, without the declaration
  changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The App is switched to all repositories
- **WHEN** the App's installation is changed to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The declared App matches
- **WHEN** the App has exactly the declared permissions and repository selection
- **THEN** the drift check reports no difference for it

### Requirement: The App's token can only write issues
A token minted for the App SHALL be able to open, edit, comment on, label, close and reopen issues in the three
repositories. It SHALL NOT be able to push, merge, edit a pull request, or change a workflow, a ruleset or a setting.

#### Scenario: Pushing with the App's token
- **WHEN** a run tries to push a commit to any branch in troupe, website or infrastructure with the App's token
- **THEN** GitHub refuses it

### Requirement: The mutation workflow's token asks for the App's declared permissions
The token the mutation workflow mints for the App SHALL ask for exactly the repository permissions the App is
declared with, metadata aside. `scripts/check.py` SHALL compare the two and fail on any difference, naming the
permission.

#### Scenario: The token asks for more than the App is declared with
- **WHEN** the workflow's token asks for a permission the App isn't declared with, such as pull requests write
- **THEN** `scripts/check.py` fails, naming that permission

### Requirement: The App's key is readable from infrastructure's main only
troupe-run/infrastructure SHALL have an environment named `mutation-issues` whose deployment branches are limited to
`main`, and which no admin can bypass. The App's private key SHALL be held only as that environment's secret
`TEST_QUALITY_APP_PRIVATE_KEY`, so a run on any other branch, or in another repository, can't read it.

#### Scenario: A run on another branch asks for the environment
- **WHEN** a workflow run on a branch other than `main` in infrastructure uses the `mutation-issues` environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from it

#### Scenario: Removing or weakening the declaration fails the check
- **WHEN** a change deletes the environment's declaration, lets it deploy from a branch other than `main`, or lets
  admins bypass it
- **THEN** `scripts/check.py` fails, naming the repository, the environment and what changed, before any plan is made

### Requirement: The App's key never passes through this repository
OpenTofu SHALL NOT hold or set the value of `TEST_QUALITY_APP_PRIVATE_KEY`. The owner SHALL set it from the password
manager with a documented command that prints nothing.

#### Scenario: A plan runs
- **WHEN** a plan runs with these declarations in place
- **THEN** it neither creates, changes nor deletes `TEST_QUALITY_APP_PRIVATE_KEY`

### Requirement: The App's client ID is declared as a repository variable
troupe-run/infrastructure SHALL have the repository variable `TEST_QUALITY_APP_CLIENT_ID`, holding the App's client
ID, declared once in this repository.

#### Scenario: The variable is changed by hand
- **WHEN** someone changes `TEST_QUALITY_APP_CLIENT_ID` on GitHub
- **THEN** the next plan shows it changing back to the declared client ID

### Requirement: The App bypasses no ruleset
The App SHALL NOT be a bypass actor on any ruleset.

#### Scenario: The rulesets after the change
- **WHEN** a plan runs with these declarations in place
- **THEN** no ruleset's bypass actors change
