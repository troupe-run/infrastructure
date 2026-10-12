# Spec Delta

## MODIFIED Requirements

### Requirement: The org's active repositories are managed
Every repository in the org that isn't archived SHALL be declared here: today `troupe`, `.github`, `infrastructure`
and `website`. Archived repositories SHALL NOT be managed.

#### Scenario: Active repositories are declared
- **WHEN** the declared repositories are compared with the org's repositories that aren't archived
- **THEN** the two lists are the same

#### Scenario: Archived repositories are left alone
- **WHEN** a plan runs
- **THEN** it reads or changes nothing in an archived repository

#### Scenario: The website keeps serving under its new name
- **WHEN** the website repository has been renamed from `troupe-run.github.io` to `website`
- **THEN** its Pages site still has the custom domain `troupe.run` with HTTPS enforced, and https://troupe.run serves
  the site
