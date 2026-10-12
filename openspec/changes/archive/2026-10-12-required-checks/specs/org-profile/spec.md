# Spec Delta

## ADDED Requirements

### Requirement: Each file in .github says where it is changed
Each file in `troupe-run/.github` SHALL carry a note naming `troupe-run/infrastructure` as its source and saying to
change it there. The note SHALL NOT appear in what GitHub renders from the file, such as the org's profile page.

#### Scenario: The contributing guide names its source
- **WHEN** someone opens `CONTRIBUTING.md` in `troupe-run/.github` as a raw file
- **THEN** its opening lines say it is written from `troupe-run/infrastructure` and changed there

#### Scenario: The note isn't rendered
- **WHEN** the org's profile page is viewed on GitHub
- **THEN** the note doesn't appear on it
