## MODIFIED Requirements

### Requirement: Every listed repository has the same release milestones
The release milestones SHALL be declared once, each with a title, a description and an open or closed state, together
with the repositories that get them. Every listed repository SHALL have every declared milestone, with the same title,
description and state.

#### Scenario: A repository without the milestones
- **WHEN** a plan runs for a listed repository that has none of the declared milestones on GitHub
- **THEN** the plan shows each declared milestone being created there, with the declared title, description and state

#### Scenario: A milestone renamed by hand
- **WHEN** someone renames a declared milestone in one repository on GitHub
- **THEN** the next plan shows the title changing back, and every issue in that milestone stays in it

#### Scenario: A declared title changes
- **WHEN** a pull request changes a declared milestone's title and a plan runs
- **THEN** the plan shows that milestone renamed in place in every listed repository, with nothing destroyed

#### Scenario: A declared description changes
- **WHEN** a pull request changes a declared milestone's description and a plan runs
- **THEN** the plan shows that milestone's description changed in place in every listed repository, with nothing
  destroyed, and every issue in it stays in it

#### Scenario: A milestone is added
- **WHEN** a pull request declares a new milestone and a plan runs
- **THEN** the plan shows it created in every listed repository, and no other milestone changes

### Requirement: A milestone made by hand is reported
The out-of-band drift check SHALL report each milestone, open or closed, on a listed repository whose title isn't
declared, naming the repository, the title and where to declare it.

#### Scenario: A milestone made on GitHub
- **WHEN** someone creates a `someday` milestone on troupe-run/website on GitHub without declaring it
- **THEN** the drift check prints a difference naming `website`, `someday` and `tofu/milestones.json`, and exits 1

#### Scenario: Every milestone is declared
- **WHEN** every milestone on every listed repository is declared
- **THEN** the drift check reports no difference for milestones
