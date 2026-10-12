# Spec Delta

## ADDED Requirements

### Requirement: Repositories allow only rebase merges
Every managed repository SHALL allow pull requests to be merged by rebase only. Merge commits and squash merges SHALL
be turned off in its settings, so the settings agree with the ruleset and GitHub offers no merge button the ruleset
would refuse.

#### Scenario: Only rebase is offered
- **WHEN** a managed repository's settings are read from GitHub
- **THEN** rebase merging is allowed, merge commits and squash merging are not, and the plan shows no difference

### Requirement: Branches are deleted on merge
Every managed repository SHALL delete a pull request's branch when the pull request is merged.

#### Scenario: A merged branch is gone
- **WHEN** a pull request in a managed repository is merged
- **THEN** its head branch no longer exists on GitHub

### Requirement: Unused features are off
Every managed repository SHALL have its wiki turned off. Classic projects SHALL be turned off on every managed
repository, unless turning them off would hide or unlink the org's project from a repository linked to it. Such a
repository SHALL keep them on, and its declaration SHALL say why.

#### Scenario: No repository has a wiki
- **WHEN** the managed repositories' settings are read from GitHub
- **THEN** none has its wiki turned on

#### Scenario: The org's roadmap stays linked
- **WHEN** the managed repositories' settings have been applied
- **THEN** the org's project is still linked to `troupe`, and still holds every item it held before
