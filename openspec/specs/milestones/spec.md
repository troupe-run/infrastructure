# milestones Specification

## Purpose
Gives every managed repository the same release milestones, declared once, so an issue in any repository can be filed
under the release it serves and the roadmap board groups them together.

## Requirements

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

### Requirement: The milestones go to every managed repository
The repositories that get the milestones SHALL be exactly the managed repositories, and `scripts/check.py` SHALL fail
when the two differ, naming each repository that is in one and not the other.

#### Scenario: A new managed repository
- **WHEN** a managed repository is added and the milestone repository list isn't updated
- **THEN** `scripts/check.py` fails, naming the repository and the file to add it to

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

### Requirement: A change to the milestones rebuilds troupe.run
A push to `main` that changes `tofu/milestones.json` SHALL dispatch troupe-run/website's `deploy.yml` on `main`, with
no inputs, so `/status/` shows the new release list once that deploy finishes. A push to `main` that doesn't change
the file, and any push to another branch, SHALL dispatch nothing. The sending job SHALL check out nothing, hold no
`GITHUB_TOKEN` permission, and use only the docs App's token (spec: docs-build-credentials).

#### Scenario: A milestone is re-described
- **WHEN** a pull request that changes a description in `tofu/milestones.json` merges to `main`
- **THEN** a website Deploy run starts on `main`, triggered by `workflow_dispatch`

#### Scenario: A push that doesn't touch the milestones
- **WHEN** a push to `main` changes other files only, such as the state commit after an apply
- **THEN** no website Deploy run is dispatched

#### Scenario: A branch that changes the milestones
- **WHEN** a push to a branch other than `main`, or a pull request, changes `tofu/milestones.json`
- **THEN** no website Deploy run is dispatched

#### Scenario: The notice is weakened
- **WHEN** a change makes the workflow run on another event or branch, gives its job a `GITHUB_TOKEN` permission or a
  checkout, drops its `docs` environment, widens the token it mints, or dispatches with inputs
- **THEN** `scripts/check.py` fails, naming what changed
