# Spec Delta

## Purpose

Gives every managed repository the same release milestones, declared once, so an issue in any repository can be filed
under the release it serves and the roadmap board groups them together.

## ADDED Requirements

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

### Requirement: The milestones go to every managed repository
The repositories that get the milestones SHALL be exactly the managed repositories, and `scripts/check.py` SHALL fail
when the two differ, naming each repository that is in one and not the other.

#### Scenario: A new managed repository
- **WHEN** a managed repository is added and the milestone repository list isn't updated
- **THEN** `scripts/check.py` fails, naming the repository and the file to add it to

### Requirement: The milestone declaration is well formed
`scripts/check.py` SHALL fail when two declared milestones share a key or a title, or when a declared state is
anything but `open` or `closed`, naming the milestone and what's wrong.

#### Scenario: A duplicate title
- **WHEN** two declared milestones are both titled `0.2.0`
- **THEN** `scripts/check.py` fails, naming `0.2.0` and saying it's declared twice

#### Scenario: An unknown state
- **WHEN** a declared milestone's state is `done`
- **THEN** `scripts/check.py` fails, naming the milestone, the value and the valid states

### Requirement: An apply never deletes a milestone
No apply SHALL delete a declared milestone, because deleting one takes it off every issue it holds. A finished
release's milestone SHALL be closed instead, by changing its declared state.

#### Scenario: A milestone removed from the declaration
- **WHEN** a pull request removes a declared milestone and a plan runs
- **THEN** the plan fails without deleting anything, and the milestone stays on GitHub with its issues

#### Scenario: A release ships
- **WHEN** a pull request sets the `0.1.0` milestone's declared state to `closed` and a plan runs
- **THEN** the plan shows `0.1.0` closed in place in every listed repository, and its issues keep it

### Requirement: Adopted milestones keep their issues
A milestone that exists on GitHub before it's declared SHALL be imported, not created, so the issues it holds stay
in it. troupe's `alpha-0` SHALL be adopted as troupe's `0.1.0`.

#### Scenario: troupe's alpha-0
- **WHEN** the milestones are first planned
- **THEN** the plan shows troupe's milestone 1 imported and renamed from `alpha-0` to `0.1.0` in place, and the
  three issues in it stay in it

### Requirement: A milestone made by hand is reported
The out-of-band drift check SHALL report each milestone, open or closed, on a listed repository whose title isn't
declared, naming the repository, the title and where to declare it.

#### Scenario: A milestone made on GitHub
- **WHEN** someone creates a `0.3.0` milestone on troupe-run/website on GitHub without declaring it
- **THEN** the drift check prints a difference naming `website`, `0.3.0` and `tofu/milestones.json`, and exits 1

#### Scenario: Every milestone is declared
- **WHEN** every milestone on every listed repository is declared
- **THEN** the drift check reports no difference for milestones
