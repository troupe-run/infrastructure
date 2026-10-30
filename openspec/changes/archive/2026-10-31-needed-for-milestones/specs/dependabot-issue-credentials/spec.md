## MODIFIED Requirements

### Requirement: The Dependabot issues App is narrow
The App `troupe-run-dependabot` SHALL have only these repository permissions: issues read/write, pull requests
read/write, Dependabot alerts read, and metadata read. It SHALL have no organisation permission. Its installation SHALL
select repositories and SHALL cover troupe, website and infrastructure. Its permissions and repository selection SHALL
be checked by the drift check, and its repository list by hand (spec: teams-and-access).

#### Scenario: The App gains a permission
- **WHEN** the App's installation gains a permission on GitHub, such as contents write, without the declaration
  changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The App is switched to all repositories
- **WHEN** the App's installation is changed to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The App gains a repository
- **WHEN** a repository other than troupe, website and infrastructure, such as `.github`, is added to the App's
  installation
- **THEN** the next hand check of its repository list, made by any change that depends on it, finds it, and it's
  removed or the declaration is changed in a pull request

#### Scenario: The declared App matches
- **WHEN** the App has exactly the declared permissions and repository selection
- **THEN** the drift check reports no difference for it

#### Scenario: The App loses its alerts permission
- **WHEN** the App's Dependabot alerts permission is removed on GitHub, or lowered to none, without the declaration
  changing
- **THEN** the drift check reports the permission and exits non-zero
