# Spec Delta

## MODIFIED Requirements

### Requirement: An apply never deletes a repository
No plan or apply SHALL delete a managed repository. Taking a repository out of this repo's management SHALL leave
it unchanged on GitHub. A plan that would destroy a repository SHALL be refused while its declaration is still
there. If its declaration is deleted, the plan SHALL show the repository being destroyed, and an approved apply SHALL
archive it rather than delete it.

#### Scenario: Taking a repository out of management leaves it as it is
- **WHEN** a repository's declaration is replaced by a `removed` block that doesn't destroy it, and a plan runs
- **THEN** the plan forgets the repository and destroys nothing, and the repository stays on GitHub as it is

#### Scenario: A destroy the declaration still names is refused
- **WHEN** the declaration is still there but would destroy the repository (it's switched off, or a change forces a
  replacement), and a plan runs
- **THEN** the plan fails, naming the repository, and nothing is applied

#### Scenario: Removing a declaration doesn't delete the repository
- **WHEN** a repository's declaration is deleted outright and a plan runs
- **THEN** the plan shows the repository being destroyed, so the owner can refuse it before approving the apply
- **AND** if the apply is approved, the repository is archived on GitHub, not deleted
