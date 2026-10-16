## MODIFIED Requirements

### Requirement: Issue types and the org project are checked for drift
The org's issue types and its project SHALL be declared in this repository, including the repositories the project
is linked to. A check SHALL report any difference between the declaration and GitHub without changing GitHub.
Whatever OpenTofu can't manage SHALL be documented as outside OpenTofu's control, with the check named as its
replacement.

#### Scenario: An issue type added by hand is reported
- **WHEN** an issue type exists on GitHub that the declaration doesn't list
- **THEN** the drift check reports it and exits non-zero, and GitHub is unchanged

#### Scenario: The declared state matches
- **WHEN** GitHub's issue types and project match the declaration
- **THEN** the drift check reports no differences and exits zero

#### Scenario: An unlinked repository is reported
- **WHEN** the org's project is unlinked from a repository the declaration lists, or linked to one it doesn't
- **THEN** the drift check reports the difference and exits non-zero, and GitHub is unchanged
