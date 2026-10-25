## MODIFIED Requirements

### Requirement: The milestone declaration is well formed
`scripts/check.py` SHALL fail when two declared milestones share a key or a title, or when a declared state is
anything but `open` or `closed`, naming the milestone and what's wrong. It SHALL also fail when an interim title isn't
a non-empty string, or is the same as any declared title or any other interim title. It SHALL also fail when a
description has a straight apostrophe (`'`) or a straight double quote (`"`), naming the milestone and the typographic
characters to use instead. It SHALL also fail on everything troupe.run's build refuses in the file: a top level that
isn't an object with a `milestones` array, a milestone that isn't an object, a title that isn't `MAJOR.MINOR.PATCH`
(ASCII digits, no leading zeros, no `v`, nothing before or after), and a description that isn't a string with
something in it besides whitespace. Each failure SHALL name the milestone, by its title when the title is a valid
version and by its position otherwise, and say how to fix it.

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

#### Scenario: A straight apostrophe in a description
- **WHEN** a declared milestone's description is "an actor that can't decide"
- **THEN** `scripts/check.py` fails, naming the milestone and saying to use ’ for an apostrophe

#### Scenario: A straight double quote in a description
- **WHEN** a declared milestone's description has `"` around a word
- **THEN** `scripts/check.py` fails, naming the milestone and saying to use “ and ” for double quotes

#### Scenario: Typographic quotes in a description
- **WHEN** every declared description uses ’, ‘, “ and ” and no straight quote
- **THEN** `scripts/check.py` reports no problem with the descriptions

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
