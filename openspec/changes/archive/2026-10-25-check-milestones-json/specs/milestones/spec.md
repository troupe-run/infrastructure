## ADDED Requirements

### Requirement: The milestone declaration is one troupe.run can build from
`scripts/check.py` SHALL fail on everything troupe.run's build refuses in `tofu/milestones.json`: a top level
that isn't an object with a `milestones` array, a milestone that isn't an object, a title that isn't
`MAJOR.MINOR.PATCH` (ASCII digits, no leading zeros, no `v`), and a description that isn't a string with something
in it besides whitespace. Each failure SHALL name the milestone, by its title when that's a valid version and by its
position otherwise, and say how to fix it.

#### Scenario: No milestones array
- **WHEN** `tofu/milestones.json` is a JSON array, or an object whose `milestones` is missing or isn't an array
- **THEN** `scripts/check.py` fails, saying the file needs a `milestones` array

#### Scenario: A milestone that isn't an object
- **WHEN** the third entry in `milestones` is a string
- **THEN** `scripts/check.py` fails, naming milestone 3 and saying each milestone must be an object

#### Scenario: A title that isn't a version
- **WHEN** a declared milestone is titled `v0.3.0`, `0.3`, `0.03.0` or `0.3.0 ` (with a trailing space)
- **THEN** `scripts/check.py` fails, naming the milestone by its position, showing the title, and saying to title it
  `MAJOR.MINOR.PATCH` with no leading zeros or `v`, as in `0.3.0`

#### Scenario: A title that isn't a string
- **WHEN** the second milestone's title is the number `3`, or the milestone has no title
- **THEN** `scripts/check.py` fails, naming milestone 2 and saying its title must be `MAJOR.MINOR.PATCH`

#### Scenario: An empty description
- **WHEN** a declared milestone's description is empty, only whitespace, not a string, or missing
- **THEN** `scripts/check.py` fails, naming the milestone and saying to describe what it adds for a user

#### Scenario: Today's declaration
- **WHEN** `scripts/check.py` runs on the `tofu/milestones.json` that troupe.run builds from today
- **THEN** it reports no problem with the declaration
