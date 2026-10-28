# board-credentials Specification

## Purpose

Declares the credential the org's automated runs use to write to the troupe roadmap board: the App's installation,
the main-only `board` environments on troupe-run/website and troupe-run/infrastructure that hold its key, and the
variable that names the App. A run uses it to put an issue it opened on the board (website's weekly link check, and
infrastructure's schedule watch and `dependabot-issues`), and to set the board's `Capability` options' descriptions
after an approved apply (spec: labels).

## Requirements

### Requirement: The board App is narrow
The board App `troupe-run-board` SHALL have exactly one permission, the organisation permission "Projects: read and
write", and no repository permission. Its installation SHALL select repositories and SHALL cover none: it reads the
public issues it adds without being installed on their repository (design D6). Its permissions and repository
selection SHALL be checked by the drift check, and its repository list by hand (spec: teams-and-access).

#### Scenario: The board App gains a permission
- **WHEN** the board App's installation gains a permission on GitHub, such as issues read or administration, without
  the declaration changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The board App is switched to all repositories
- **WHEN** the board App's installation is changed to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The board App gains a repository
- **WHEN** a repository is added to the board App's installation
- **THEN** the next hand check of its repository list, made by any change that depends on it, finds it, and it's
  removed or the declaration is changed in a pull request

#### Scenario: The declared board App matches
- **WHEN** the board App has exactly the declared permission and repository selection
- **THEN** the drift check reports no difference for it

### Requirement: The board key is readable from main only
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

### Requirement: The board App bypasses no ruleset
The board App SHALL NOT be a bypass actor on any ruleset. It writes nothing to a repository's contents.

#### Scenario: website's rulesets after the change
- **WHEN** a plan runs with the board declarations in place
- **THEN** no ruleset's bypass actors change
