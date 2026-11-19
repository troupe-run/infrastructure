# Spec Delta

## Purpose

Declares the credential auto-merge queues pull requests with: the `troupe-run-merge` App, its permissions and
installation, and the main-only `auto-merge` environment on infrastructure that alone holds its key.

## ADDED Requirements

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

### Requirement: The merge App's token can't change code or settings
A token minted for the merge App SHALL NOT be able to push to a branch, change a repository's settings, rulesets,
environments or variables, or merge a pull request except through the merge queue.

#### Scenario: Pushing
- **WHEN** the token is used to create a branch or a commit in troupe
- **THEN** GitHub refuses it with 403

#### Scenario: Changing a variable
- **WHEN** the token is used to set troupe's `AUTO_MERGE`
- **THEN** GitHub refuses it with 403

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
