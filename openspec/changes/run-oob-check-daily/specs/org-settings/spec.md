## MODIFIED Requirements

### Requirement: Issue types and the org project are checked for drift
The org's issue types and its project SHALL be declared in this repository, including the repositories the project
is linked to. A check SHALL report any difference between the declaration and GitHub without changing GitHub. The
check SHALL run in CI whenever `main` is planned, daily included (spec: ci-apply), as well as by hand. Whatever
OpenTofu can't manage SHALL be documented as outside OpenTofu's control, with the check named as its replacement. A
value the check can't read SHALL be an error, never "no difference" and never a difference.

#### Scenario: An issue type added by hand is reported
- **WHEN** an issue type exists on GitHub that the declaration doesn't list
- **THEN** the drift check reports it and exits non-zero, and GitHub is unchanged

#### Scenario: The declared state matches
- **WHEN** GitHub's issue types and project match the declaration
- **THEN** the drift check reports no differences and exits zero

#### Scenario: An unlinked repository is reported
- **WHEN** the org's project is unlinked from a repository the declaration lists, or linked to one it doesn't
- **THEN** the drift check reports the difference and exits non-zero, and GitHub is unchanged

#### Scenario: An issue type changed by hand is caught within a day
- **WHEN** an owner changes an issue type's description on GitHub, and nobody runs the check by hand
- **THEN** the next daily run of `main`'s plan fails its drift job, naming the issue type and the field

#### Scenario: A refused read is an error
- **WHEN** GitHub refuses one of the check's reads (401, 403, or a GraphQL answer carrying errors)
- **THEN** the drift check exits non-zero with an error naming that check and saying its state is unknown, and
  doesn't report "no differences"

#### Scenario: A value hidden from the reader is an error
- **WHEN** GitHub answers a read but returns a declared field as `null` because the credential can't see it, such as
  whether 2FA is required
- **THEN** the drift check exits non-zero with an error naming the check and the field, not a difference saying the
  field is `None`
