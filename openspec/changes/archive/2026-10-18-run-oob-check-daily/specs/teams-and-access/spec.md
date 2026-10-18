## MODIFIED Requirements

### Requirement: Each App's installation is declared and checked
For each GitHub App installed in the org (today DCO, `troupe-run-infrastructure`, `troupe-run-release` and
`troupe-run-board`), its permissions and its repository selection (all repositories, or selected ones) SHALL be
declared here. A difference from GitHub SHALL be reported by a drift check that only reads. The check SHALL run in CI
whenever `main` is planned, daily included (spec: ci-apply), as well as by hand.

#### Scenario: An App given a new permission is reported
- **WHEN** an App's installation gains a permission on GitHub without the declaration changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: An App switched to all repositories is reported
- **WHEN** an App's installation is changed from selected repositories to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The declared installations match
- **WHEN** each App's permissions and repository selection match the declaration
- **THEN** the drift check reports no difference

#### Scenario: A permission granted by hand is caught within a day
- **WHEN** an owner grants an App a new permission on GitHub, and nobody runs the check by hand
- **THEN** the next daily run of `main`'s plan fails its drift job, naming the App and the permission
