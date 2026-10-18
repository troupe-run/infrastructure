# Spec Delta

## Purpose

Declares the credential an automated run uses to put an issue it opened on the troupe roadmap board: the App's
installation, the main-only environment on troupe-run/website that holds its key, and the variable that names the App.

## ADDED Requirements

### Requirement: The board App is narrow
The board App `troupe-run-board` SHALL have the organisation permission "Projects: read and write" and no other
permission that can write. Its repository permissions SHALL be no wider than metadata and issues read. Its
installation SHALL select repositories and SHALL cover `troupe-run/website` only. Any difference SHALL be reported by
the drift check (spec: teams-and-access).

#### Scenario: The board App gains a permission
- **WHEN** the board App's installation gains a permission on GitHub, such as issues write or administration, without
  the declaration changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The board App is switched to all repositories
- **WHEN** the board App's installation is changed to all repositories, or gains a repository
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The declared board App matches
- **WHEN** the board App has exactly the declared permissions and selected repositories
- **THEN** the drift check reports no difference for it

### Requirement: The board key is readable from website's main only
troupe-run/website SHALL have an environment named `board` whose deployment branches are limited to `main`, and which
no admin can bypass. The App's private key SHALL be held only as that environment's secret `BOARD_APP_PRIVATE_KEY`,
so a workflow run on any other branch, or in any other repository, can't read it.

#### Scenario: A run on another branch asks for the environment
- **WHEN** a workflow run on a branch other than `main` uses the `board` environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from it

#### Scenario: The branch policy is changed by hand
- **WHEN** someone widens the `board` environment's deployment branches, or allows admins to bypass them, on GitHub
- **THEN** the next plan shows the change being reverted

#### Scenario: Removing or weakening the declaration fails the check
- **WHEN** a change deletes the `board` environment's declaration, lets it deploy from a branch other than `main`, or
  lets admins bypass it
- **THEN** `scripts/check.py` fails, naming the environment and what changed, before any plan is made

### Requirement: The board key's value never passes through this repository
OpenTofu SHALL NOT hold or set the value of `BOARD_APP_PRIVATE_KEY`. The owner SHALL set it from the password manager
with a documented command that prints nothing. Checking that it's set SHALL read its name only.

#### Scenario: The key is set
- **WHEN** the owner has run the documented command
- **THEN** listing the `board` environment's secrets on website shows `BOARD_APP_PRIVATE_KEY` by name, and no value
  appears in the repository, the state, a plan or a log

#### Scenario: A plan runs
- **WHEN** a plan runs with the board declarations in place
- **THEN** it neither creates, changes nor deletes `BOARD_APP_PRIVATE_KEY`

### Requirement: The board App's client ID is declared as a repository variable
troupe-run/website SHALL have the repository variable `BOARD_APP_CLIENT_ID`, holding the board App's client ID,
declared in this repository. A different value on GitHub, or the variable's removal, SHALL show in the next plan.

#### Scenario: The variable is changed by hand
- **WHEN** someone changes `BOARD_APP_CLIENT_ID` on website on GitHub
- **THEN** the next plan shows it changing back to the declared client ID

#### Scenario: The variable is deleted by hand
- **WHEN** someone deletes `BOARD_APP_CLIENT_ID` from website
- **THEN** the next plan shows it being created with the declared client ID

### Requirement: The board App bypasses no ruleset
The board App SHALL NOT be a bypass actor on any ruleset. It writes nothing to a repository's contents.

#### Scenario: website's rulesets after the change
- **WHEN** a plan runs with the board declarations in place
- **THEN** no ruleset's bypass actors change
