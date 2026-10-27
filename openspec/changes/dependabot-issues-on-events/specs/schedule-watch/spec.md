# Spec Delta

## MODIFIED Requirements

### Requirement: The watched workflows are declared in one place
The watched workflows SHALL be declared as data in one file in this repository. Each entry SHALL name the repository,
the workflow file and the age limit in days. An entry with a missing, unknown or malformed field SHALL fail the run,
naming the entry and the field, and SHALL NOT be skipped.

#### Scenario: website's weekly check is watched
- **WHEN** the declaration is read
- **THEN** it lists `troupe-run/website`'s `.github/workflows/links-weekly.yml` with an age limit of 8 days

#### Scenario: The Dependabot issues backstop is watched
- **WHEN** the declaration is read
- **THEN** it lists `troupe-run/infrastructure`'s `.github/workflows/dependabot-issues.yml` with an age limit of 2
  days

#### Scenario: A malformed entry
- **WHEN** an entry's age limit is not a positive whole number, or the entry has a field the declaration doesn't
  define
- **THEN** the run fails before reading GitHub, naming the entry and the field, and the tracking issue is untouched
