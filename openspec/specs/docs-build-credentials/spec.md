# docs-build-credentials Specification

## Purpose

Declares the credential troupe's workflows use to start the website's docs build, and where it may be read: the docs
App's installation on troupe-run/website, the `docs` environment on troupe that holds its key, and the variable that
names the App.

## Requirements

### Requirement: The docs App is narrow and installed on website only
The docs App `troupe-run-docs` SHALL have only these repository permissions: actions read/write, and metadata read.
It SHALL have no organisation permissions. Its installation SHALL select repositories, and SHALL cover
`troupe-run/website` only. Any difference SHALL be reported by the drift check or the hand-confirmed list (spec:
teams-and-access).

#### Scenario: The docs App gains a permission
- **WHEN** the docs App's installation gains a permission on GitHub, such as contents write, without the declaration
  changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The docs App is switched to all repositories
- **WHEN** the docs App's installation is changed to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The docs App gains a repository
- **WHEN** a repository other than website, such as troupe, is added to the docs App's installation
- **THEN** the next hand check of its repository list, made by any change that depends on it, finds it, and it's
  removed or the declaration is changed in a pull request

#### Scenario: The declared docs App matches
- **WHEN** the docs App has exactly the declared permissions and repository selection
- **THEN** the drift check reports no difference for it

### Requirement: The docs App's token starts website workflows and writes nothing else
A token minted for the docs App SHALL be able to start a `workflow_dispatch` run of a workflow in troupe-run/website.
It SHALL NOT be able to write the website's contents: no push to any branch, and no tag or release.

#### Scenario: Starting the website's build
- **WHEN** a troupe workflow mints the docs App's token and creates a `workflow_dispatch` event for a website
  workflow that accepts one, on `main`
- **THEN** GitHub starts a run of that workflow

#### Scenario: Writing the website's contents
- **WHEN** the same token is used to create a branch, a tag or a file in troupe-run/website
- **THEN** GitHub refuses it with 403, and nothing in the repository changes

### Requirement: The docs key is readable from troupe's main only
troupe-run/troupe SHALL have an environment named `docs` whose deployment branches are limited to `main`, and which
no admin can bypass. The App's private key SHALL be held only as that environment's secret `DOCS_APP_PRIVATE_KEY`, so
a workflow run on any other branch, on a tag, or in any other repository can't read it.

#### Scenario: A run on another branch or a tag asks for the environment
- **WHEN** a workflow run in troupe on a branch other than `main`, or on a tag, uses the `docs` environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from it

#### Scenario: The branch policy is changed by hand
- **WHEN** someone widens the `docs` environment's deployment branches, or allows admins to bypass them, on GitHub
- **THEN** the next plan shows the change being reverted

#### Scenario: Removing or weakening the declaration fails the check
- **WHEN** a change deletes the `docs` environment's declaration, lets it deploy from a branch other than `main`, or
  lets admins bypass it
- **THEN** `scripts/check.py` fails, naming the repository, the environment and what changed, before any plan is made

### Requirement: The docs key's value never passes through this repository
OpenTofu SHALL NOT hold or set the value of `DOCS_APP_PRIVATE_KEY`. The owner SHALL set it from the password manager
with a documented command that prints nothing. Checking that it's set SHALL read its name only.

#### Scenario: The key is set
- **WHEN** the owner has run the documented command
- **THEN** listing the `docs` environment's secrets on troupe shows `DOCS_APP_PRIVATE_KEY` by name, and no value
  appears in the repository, the state, a plan or a log

#### Scenario: A plan runs
- **WHEN** a plan runs with the docs declarations in place
- **THEN** it neither creates, changes nor deletes `DOCS_APP_PRIVATE_KEY`

### Requirement: The docs App's client ID is declared as a repository variable
troupe-run/troupe SHALL have the repository variable `DOCS_APP_CLIENT_ID`, holding the docs App's client ID, declared
in this repository. A different value on GitHub, or the variable's removal, SHALL show in the next plan.

#### Scenario: The variable is changed by hand
- **WHEN** someone changes `DOCS_APP_CLIENT_ID` on troupe on GitHub
- **THEN** the next plan shows it changing back to the declared client ID

#### Scenario: The variable is deleted by hand
- **WHEN** someone deletes `DOCS_APP_CLIENT_ID` from troupe
- **THEN** the next plan shows it being created with the declared client ID

### Requirement: The docs App bypasses no ruleset
The docs App SHALL NOT be a bypass actor on any ruleset. It writes nothing to a repository's contents.

#### Scenario: Rulesets after the change
- **WHEN** a plan runs with the docs declarations in place
- **THEN** no ruleset's bypass actors change
