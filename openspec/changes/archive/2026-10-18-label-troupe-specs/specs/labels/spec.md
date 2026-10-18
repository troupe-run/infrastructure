## ADDED Requirements

### Requirement: Kinds of work beyond GitHub's defaults are declared once
Labels for a kind of work that any repository can have and that GitHub's default labels don't cover, such as
`speed`, SHALL be declared once, each with a colour and a description of at most 100 characters that says what work
it marks, and SHALL be part of every managed repository's label set, with the same colour and description in each.
A capability label SHALL NOT be used to mark a kind of work.

#### Scenario: The speed label is created everywhere
- **WHEN** a plan runs after `speed` is declared
- **THEN** it shows `speed` being created on troupe, `.github`, infrastructure and website with the declared colour and
  description, and no other label changing

#### Scenario: A kind label's description over GitHub's limit
- **WHEN** a declared kind label's description is longer than 100 characters
- **THEN** `scripts/check.py` fails, naming the label and its length

#### Scenario: A kind label edited by hand
- **WHEN** someone changes `speed`'s colour or description on one repository on GitHub
- **THEN** the next plan shows it changing back there, and the label stays on every issue that carries it
