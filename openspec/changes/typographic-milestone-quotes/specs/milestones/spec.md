## MODIFIED Requirements

### Requirement: The milestone declaration is well formed
`scripts/check.py` SHALL fail when two declared milestones share a key or a title, or when a declared state is
anything but `open` or `closed`, naming the milestone and what's wrong. It SHALL also fail when an interim title isn't
a non-empty string, or is the same as any declared title or any other interim title. It SHALL also fail when a
description has a straight apostrophe (`'`) or a straight double quote (`"`), naming the milestone and the typographic
characters to use instead.

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
