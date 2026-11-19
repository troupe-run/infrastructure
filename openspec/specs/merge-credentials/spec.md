# merge-credentials Specification

## Purpose
Declares the credential auto-merge queues pull requests with: the `troupe-run-merge` App, its permissions and
installation, and the main-only `auto-merge` environment on infrastructure that alone holds its key.

## Requirements

### Requirement: The merge App is narrow
The App `troupe-run-merge` SHALL have only the repository permissions auto-merge needs to read pull requests, their
checks, reviews, issues and variables, to comment on and label pull requests, and to add them to or remove them from
the merge queue. It SHALL have no organisation permission. Its permissions SHALL be declared in `oob/` and checked by
the drift check.

#### Scenario: The merge App gains a permission
- **WHEN** the App's installation gains a permission on GitHub, such as administration, without the declaration
  changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The declared merge App matches
- **WHEN** the App has exactly the declared permissions and repository selection
- **THEN** the drift check reports no difference for it

### Requirement: The merge App is installed on the three governed repositories
The App's installation SHALL select repositories, and SHALL cover exactly troupe-run/troupe, troupe-run/infrastructure
and troupe-run/website. Its repository list SHALL be confirmed by hand, as for every App (spec: teams-and-access).

#### Scenario: The merge App is switched to all repositories
- **WHEN** the App's installation is changed to all repositories
- **THEN** the drift check reports it and exits non-zero

### Requirement: The merge App's token can't change main, settings or variables, or merge past the queue
A token minted for the merge App SHALL NOT be able to change `main` except through the merge queue, change a
repository's settings, rulesets, environments or variables, or merge a pull request directly. Queueing needs contents
write, which lets it push other branches. A push by it SHALL never be auto-queued (spec: auto-merge).

#### Scenario: Merging directly
- **WHEN** the token is used to merge a pull request with the REST merge endpoint
- **THEN** GitHub refuses it, saying changes must be made through the merge queue

#### Scenario: Changing a variable
- **WHEN** the token is used to set troupe's `AUTO_MERGE`
- **THEN** GitHub refuses it with 403

#### Scenario: Queueing needs contents write
- **WHEN** the token has contents read and asks to queue a pull request
- **THEN** GitHub refuses it with 403, so the App is declared with contents write

#### Scenario: A push by the App onto a person's pull request
- **WHEN** the token pushes a commit onto a person's open pull request branch
- **THEN** the pull request is never queued by auto-merge on that head or any later head that contains the commit

### Requirement: The merge key is readable from infrastructure's main only
troupe-run/infrastructure SHALL have an environment named `auto-merge` whose deployment branches are limited to
`main`, and which no admin can bypass. The App's private key SHALL be held only as that environment's secret
`MERGE_APP_PRIVATE_KEY`, and its client ID as the variable `MERGE_APP_CLIENT_ID`.

#### Scenario: A run on a branch asks for the environment
- **WHEN** a workflow run on a branch other than `main` names the `auto-merge` environment
- **THEN** GitHub refuses the deployment, and the run can't read the key

#### Scenario: The environment is weakened
- **WHEN** the `auto-merge` environment is declared without its main-only branch policy
- **THEN** the main-only environments test fails

#### Scenario: troupe and website hold no key
- **WHEN** troupe's and website's environments and secrets are listed
- **THEN** neither holds the merge App's key
