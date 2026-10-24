## ADDED Requirements

### Requirement: A milestone can carry an interim title
A declared milestone MAY have an interim title. While it's declared, every listed repository SHALL give that milestone
the interim title on GitHub instead of its title. Its title SHALL stay the release's version. Removing the interim title
SHALL rename the milestone to its title in place.

#### Scenario: Titles that swap
- **WHEN** a pull request swaps the titles of two declared milestones, gives each an interim title, and a plan runs
- **THEN** the plan shows each renamed in place to its interim title, the apply succeeds, and every issue stays in its
  milestone

#### Scenario: The interim titles are removed
- **WHEN** a later pull request removes those interim titles and a plan runs
- **THEN** the plan shows each milestone renamed in place to its declared title, with nothing destroyed, and it
  applies

#### Scenario: A swap without interim titles
- **WHEN** two declared milestones' titles are swapped in one pull request without interim titles, and it's applied
- **THEN** GitHub refuses the rename, because the title is already in use in that repository

## MODIFIED Requirements

### Requirement: The milestone declaration is well formed
`scripts/check.py` SHALL fail when two declared milestones share a key or a title, or when a declared state is
anything but `open` or `closed`, naming the milestone and what's wrong. It SHALL also fail when an interim title isn't
a non-empty string, or is the same as any declared title or any other interim title.

#### Scenario: A duplicate title
- **WHEN** two declared milestones are both titled `0.2.0`
- **THEN** `scripts/check.py` fails, naming `0.2.0` and saying it's declared twice

#### Scenario: An unknown state
- **WHEN** a declared milestone's state is `done`
- **THEN** `scripts/check.py` fails, naming the milestone, the value and the valid states

#### Scenario: An interim title that's a declared title
- **WHEN** a declared milestone's interim title is `0.3.0`, and another milestone is titled `0.3.0`
- **THEN** `scripts/check.py` fails, naming the milestone and `0.3.0`, and saying an interim title must be a title no
  milestone has

#### Scenario: An empty interim title
- **WHEN** a declared milestone's interim title is an empty string
- **THEN** `scripts/check.py` fails, naming the milestone and saying an interim title must be a non-empty string

### Requirement: A milestone made by hand is reported
The out-of-band drift check SHALL report each milestone, open or closed, on a listed repository whose title isn't
declared, naming the repository, the title and where to declare it. A declared milestone's title and its interim
title SHALL both count as declared.

#### Scenario: A milestone made on GitHub
- **WHEN** someone creates a `someday` milestone on troupe-run/website on GitHub without declaring it
- **THEN** the drift check prints a difference naming `website`, `someday` and `tofu/milestones.json`, and exits 1

#### Scenario: Every milestone is declared
- **WHEN** every milestone on every listed repository is declared
- **THEN** the drift check reports no difference for milestones

#### Scenario: A milestone under its interim title
- **WHEN** a declared milestone has an interim title, and GitHub has that milestone under either its interim title or
  its title
- **THEN** the drift check reports no difference for it
