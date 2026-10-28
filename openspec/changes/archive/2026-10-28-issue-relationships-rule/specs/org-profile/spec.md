## ADDED Requirements

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
- **WHEN** someone reads the Milestones section's rule for completed work
- **THEN** its "the work it arose from" points to the guide's "arose from" line

### Requirement: The guide's issue types are the org's
The org's contributing guide SHALL say that every issue has a type, and SHALL list exactly the issue types enabled
in `oob/issue-types.json`. A type it lists that isn't enabled there, or an enabled type it leaves out, SHALL fail the
repository's check, naming the type and which way they disagree.

#### Scenario: The guide matches the declaration
- **WHEN** the guide lists Epic, Feature, Bug, Task and Decision, and those are the enabled types
- **THEN** the check reports no problem with the guide's types

#### Scenario: A type the org doesn't have
- **WHEN** the guide lists Chore, and `oob/issue-types.json` has no enabled type called Chore
- **THEN** the check fails, naming Chore and saying it isn't an enabled issue type

#### Scenario: A type the guide leaves out
- **WHEN** `oob/issue-types.json` enables Task, and the guide's list doesn't name it
- **THEN** the check fails, naming Task and saying the guide doesn't list it

#### Scenario: The guide has no list
- **WHEN** the guide no longer says that every issue has a type
- **THEN** the check fails, saying the guide's list of issue types wasn't found
