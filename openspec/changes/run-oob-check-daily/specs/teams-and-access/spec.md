## MODIFIED Requirements

### Requirement: Each App's installation is declared and checked
For each GitHub App installed in the org (today DCO, `troupe-run-infrastructure` and `troupe-run-release`), its
permissions and its repository selection (all repositories, or selected ones) SHALL be declared here. A difference
from GitHub SHALL be reported by a drift check that only reads. No token CI holds can read the org's installations,
so this check SHALL be run by hand. CI's drift job SHALL name it as not run in every run (spec: ci-apply).

#### Scenario: An App given a new permission is reported
- **WHEN** an App's installation gains a permission on GitHub without the declaration changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: An App switched to all repositories is reported
- **WHEN** an App's installation is changed from selected repositories to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The declared installations match
- **WHEN** each App's permissions and repository selection match the declaration
- **THEN** the drift check reports no difference

#### Scenario: CI says the installation check is left to a person
- **WHEN** CI's drift job runs
- **THEN** it doesn't read the org's installations, and its output names the App-installations check as run by hand
