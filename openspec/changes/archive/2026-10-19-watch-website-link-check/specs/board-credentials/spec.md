# Spec Delta

## MODIFIED Requirements

### Requirement: The board key is readable from website's main only
troupe-run/website and troupe-run/infrastructure SHALL each have an environment named `board` whose deployment
branches are limited to `main`, and which no admin can bypass. The App's private key SHALL be held only as those
environments' secret `BOARD_APP_PRIVATE_KEY`, so a workflow run on any other branch, or in any other repository, can't
read it.

#### Scenario: A run on another branch asks for the environment
- **WHEN** a workflow run on a branch other than `main`, in website or infrastructure, uses the `board` environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from it

#### Scenario: The branch policy is changed by hand
- **WHEN** someone widens either `board` environment's deployment branches, or allows admins to bypass them, on
  GitHub
- **THEN** the next plan shows the change being reverted

#### Scenario: Removing or weakening the declaration fails the check
- **WHEN** a change deletes either `board` environment's declaration, lets it deploy from a branch other than `main`,
  or lets admins bypass it
- **THEN** `scripts/check.py` fails, naming the repository, the environment and what changed, before any plan is made

### Requirement: The board key's value never passes through this repository
OpenTofu SHALL NOT hold or set the value of `BOARD_APP_PRIVATE_KEY` in any repository. The owner SHALL set it from
the password manager with a documented command that prints nothing. Checking that it's set SHALL read its name only.

#### Scenario: The key is set
- **WHEN** the owner has run the documented command for website and for infrastructure
- **THEN** listing each `board` environment's secrets shows `BOARD_APP_PRIVATE_KEY` by name, and no value appears in
  the repository, the state, a plan or a log

#### Scenario: A plan runs
- **WHEN** a plan runs with the board declarations in place
- **THEN** it neither creates, changes nor deletes `BOARD_APP_PRIVATE_KEY` in either repository

### Requirement: The board App's client ID is declared as a repository variable
troupe-run/website and troupe-run/infrastructure SHALL each have the repository variable `BOARD_APP_CLIENT_ID`,
holding the board App's client ID, declared once in this repository. A different value on GitHub, or the variable's
removal, SHALL show in the next plan.

#### Scenario: The variable is changed by hand
- **WHEN** someone changes `BOARD_APP_CLIENT_ID` on website or infrastructure on GitHub
- **THEN** the next plan shows it changing back to the declared client ID

#### Scenario: The variable is deleted by hand
- **WHEN** someone deletes `BOARD_APP_CLIENT_ID` from website or infrastructure
- **THEN** the next plan shows it being created with the declared client ID
