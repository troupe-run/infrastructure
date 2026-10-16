## MODIFIED Requirements

### Requirement: Unused features are off
Every managed repository SHALL have its wiki turned off. Classic projects SHALL be turned off on every managed
repository, unless turning them off would hide or unlink the org's project from a repository linked to it. Such a
repository SHALL keep them on, and its declaration SHALL say why.

#### Scenario: No repository has a wiki
- **WHEN** the managed repositories' settings are read from GitHub
- **THEN** none has its wiki turned on

#### Scenario: The org's roadmap stays linked
- **WHEN** the managed repositories' settings have been applied
- **THEN** the org's project is still linked to `troupe` and `website`, and still holds every item it held before
