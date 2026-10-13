## ADDED Requirements

### Requirement: A capability label says what it covers
Each of troupe's `cap:*` labels SHALL have a description of at most 100 characters that says what the capability
covers, not one that only repeats its name. Where troupe has not yet defined a capability, its description SHALL be
`TBD` rather than a guess.

#### Scenario: A description that repeats the name
- **WHEN** a declared `cap:<name>` label's description is `Capability: <name>`
- **THEN** `scripts/check.py` fails, naming the label

#### Scenario: A description over GitHub's limit
- **WHEN** a declared `cap:*` label's description is longer than 100 characters
- **THEN** `scripts/check.py` fails, naming the label and its length

#### Scenario: A capability troupe hasn't defined
- **WHEN** a `cap:*` label has no spec, glossary entry or issue that defines it
- **THEN** its declared description is `TBD`, and `scripts/check.py` passes

### Requirement: A description written from a spec records that spec's Purpose
A `cap:<name>` label whose troupe spec `<name>` exists SHALL have the Purpose its description was written from
recorded in this repository, verbatim, next to the other out-of-band declarations.

#### Scenario: A labelled spec with no recorded Purpose
- **WHEN** troupe's `openspec/specs/` on `main` holds `<name>`, `cap:<name>` is declared, and no Purpose is recorded
  for `cap:<name>`
- **THEN** the drift check prints a difference naming `cap:<name>` and saying its description hasn't been checked
  against the spec's Purpose, and exits 1

### Requirement: A description that may be stale is reported
The out-of-band drift check SHALL report each `cap:<name>` label whose troupe spec's Purpose on `main` differs from
the Purpose recorded for it, naming the label and where to update the description and the record. Differences in
line wrapping or surrounding whitespace SHALL NOT count as a change.

#### Scenario: troupe rewrites a spec's Purpose
- **WHEN** the Purpose of troupe's `runs` spec on `main` differs from the Purpose recorded for `cap:runs`
- **THEN** the drift check prints a difference naming `cap:runs`, `tofu/labels/troupe.json` and the record, and
  exits 1

#### Scenario: troupe only re-wraps a Purpose
- **WHEN** the Purpose of troupe's `runs` spec differs from the recorded one only in line breaks or spacing
- **THEN** the drift check reports nothing about `cap:runs`

#### Scenario: Every recorded Purpose matches
- **WHEN** every labelled troupe spec's Purpose matches the Purpose recorded for its label
- **THEN** the drift check reports no difference for troupe's label descriptions
