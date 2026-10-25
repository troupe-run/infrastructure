# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The docs key is readable from troupe's main only`
- TO: `### Requirement: The docs key is readable from main only`

## MODIFIED Requirements

### Requirement: The docs key is readable from main only
troupe-run/troupe and troupe-run/infrastructure SHALL each have an environment named `docs` whose deployment branches
are limited to `main`, and which no admin can bypass. The App's private key SHALL be held only as those environments'
secret `DOCS_APP_PRIVATE_KEY`, so a workflow run on any other branch, on a tag, or in any other repository can't read
it.

#### Scenario: A run on another branch or a tag asks for the environment
- **WHEN** a workflow run in troupe or infrastructure, on a branch other than `main` or on a tag, uses the `docs`
  environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from it

#### Scenario: The branch policy is changed by hand
- **WHEN** someone widens either `docs` environment's deployment branches, or allows admins to bypass them, on GitHub
- **THEN** the next plan shows the change being reverted

#### Scenario: Removing or weakening the declaration fails the check
- **WHEN** a change deletes either `docs` environment's declaration, lets it deploy from a branch other than `main`,
  or lets admins bypass it
- **THEN** `scripts/check.py` fails, naming the repository, the environment and what changed, before any plan is made

### Requirement: The docs key's value never passes through this repository
OpenTofu SHALL NOT hold or set the value of `DOCS_APP_PRIVATE_KEY` in any repository. The owner SHALL set it from the
password manager with a documented command that prints nothing. Checking that it's set SHALL read its name only.

#### Scenario: The key is set
- **WHEN** the owner has run the documented command for troupe and for infrastructure
- **THEN** listing each `docs` environment's secrets shows `DOCS_APP_PRIVATE_KEY` by name, and no value appears in
  the repository, the state, a plan or a log

#### Scenario: A plan runs
- **WHEN** a plan runs with the docs declarations in place
- **THEN** it neither creates, changes nor deletes `DOCS_APP_PRIVATE_KEY`

### Requirement: The docs App's client ID is declared as a repository variable
troupe-run/troupe and troupe-run/infrastructure SHALL each have the repository variable `DOCS_APP_CLIENT_ID`, holding
the docs App's client ID, declared once in this repository. A different value on GitHub, or the variable's removal,
SHALL show in the next plan.

#### Scenario: The variable is changed by hand
- **WHEN** someone changes `DOCS_APP_CLIENT_ID` on troupe or infrastructure on GitHub
- **THEN** the next plan shows it changing back to the declared client ID

#### Scenario: The variable is deleted by hand
- **WHEN** someone deletes `DOCS_APP_CLIENT_ID` from troupe or infrastructure
- **THEN** the next plan shows it being created with the declared client ID
