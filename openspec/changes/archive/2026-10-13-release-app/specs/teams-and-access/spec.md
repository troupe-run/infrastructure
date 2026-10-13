# Spec Delta

## MODIFIED Requirements

### Requirement: Each App's installation is declared and checked
For each GitHub App installed in the org (today DCO, `troupe-run-infrastructure` and `troupe-run-release`), its
permissions and its repository selection (all repositories, or selected ones) SHALL be declared here. A difference
from GitHub SHALL be reported by a drift check that only reads.

#### Scenario: An App given a new permission is reported
- **WHEN** an App's installation gains a permission on GitHub without the declaration changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: An App switched to all repositories is reported
- **WHEN** an App's installation is changed from selected repositories to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The declared installations match
- **WHEN** each App's permissions and repository selection match the declaration
- **THEN** the drift check reports no difference

### Requirement: No App is installed that nothing uses
Each App installed in the org SHALL be used by something this repository declares or documents. An App that nothing
uses SHALL be deleted, and its declaration and its keys removed with it.

#### Scenario: The declared installations are only the ones in use
- **WHEN** the drift check reads the org's App installations
- **THEN** it finds exactly DCO, `troupe-run-infrastructure` and `troupe-run-release`, and reports no difference

#### Scenario: The release App is used
- **WHEN** someone asks what uses `troupe-run-release`
- **THEN** this repository names troupe's release workflow (troupe-run/troupe#23) and the `release` environment and
  variable it declares for it (spec: release-credentials)
