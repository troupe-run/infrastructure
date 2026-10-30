## MODIFIED Requirements

### Requirement: The guide says how issues are related
The org's contributing guide SHALL say that a sub-issue of an Epic is a part of one outcome, in any repository, and
that an issue with sub-issues is an Epic; that blocked by is a real prerequisite, a Decision included; and that an
"arose from" line in the body says where a follow-up came from. It SHALL say that a follow-up needed for an outcome
that has an Epic becomes a sub-issue of that Epic, and that any other follow-up gets only the "arose from" line.

#### Scenario: Work found while doing a change
- **WHEN** a contributor finds work while doing a change whose issue is a sub-issue of an Epic, and the outcome
  needs that work
- **THEN** the guide tells them to file it as a sub-issue of that Epic, with an "arose from" line naming the issue
  it came from

#### Scenario: A follow-up the outcome doesn't need
- **WHEN** a contributor files a follow-up that is parked, optional or a new outcome of its own, or whose origin has
  no Epic
- **THEN** the guide tells them to give it only the "arose from" line

#### Scenario: A prerequisite
- **WHEN** an issue can't start until a Decision is made
- **THEN** the guide tells them to mark the issue as blocked by the Decision

#### Scenario: The milestone rule reads the same line
- **WHEN** someone reads the Milestones section's rule for follow-ups
- **THEN** it links to the guide's "How issues are related", and gives the origin's milestone only to a follow-up the
  origin needs: a sub-issue of its Epic, or an issue blocking it

## ADDED Requirements

### Requirement: The guide says a milestone holds only what its release needs
The org's contributing guide SHALL say that an issue goes in a milestone only if that release would wait for it,
because part of the milestone's description needs it, and that every other issue has no milestone, open or closed. It
SHALL say a follow-up takes its origin's milestone only when the origin needs it, and SHALL NOT say that completed
work always has a milestone.

#### Scenario: An improvement found while doing a change
- **WHEN** a contributor files an improvement that arose from an issue in `0.1.0`, and nothing in `0.1.0` needs it
- **THEN** the guide tells them to give it the "arose from" line and no milestone

#### Scenario: Work the origin needs
- **WHEN** a contributor files work that an issue in `0.1.0` can't be finished without
- **THEN** the guide tells them to put it in `0.1.0`, as a sub-issue of the origin's Epic or blocking the origin

#### Scenario: Upkeep with no release
- **WHEN** a contributor files process upkeep, a flaky test outside an Epic a release needs, or a version bump
- **THEN** the guide tells them it has no milestone, and keeps none once it's closed

#### Scenario: A Decision
- **WHEN** a contributor files a Decision that blocks work in `0.2.0`
- **THEN** the guide tells them to put it in `0.2.0`, the milestone of the earliest work it blocks

#### Scenario: A Decision that blocks nothing
- **WHEN** a contributor files a Decision that shaped work but blocks none
- **THEN** the guide tells them it has no milestone (owner, 2026-10-30, on #229)

### Requirement: The guide says closing a milestone reviews the issues with no milestone
The org's contributing guide SHALL say that when a milestone is closed, by a pull request setting its state to `closed`
in `tofu/milestones.json`, every open issue with no milestone is looked at and given one outcome: moved into a
milestone, labelled `parked` with a reason to come back, or closed as not planned. It SHALL say that pull request's
plan lists those issues.

#### Scenario: A release closes
- **WHEN** a contributor prepares the pull request that closes `0.1.0`
- **THEN** the guide tells them to give each open issue with no milestone one of the three outcomes, and where the
  list is shown
