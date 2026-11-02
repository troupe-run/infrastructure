## ADDED Requirements

### Requirement: An entry ignores only the dependencies declared for it
The dependencies each repository's Dependabot entry ignores SHALL be declared in one place in this repository, per
repository and ecosystem, as a list of names in which `*` matches any characters. Each name SHALL be rendered as an
`ignore` condition naming only that dependency, in that repository's entry for that ecosystem. An entry with no
declared names SHALL have no `ignore`.

#### Scenario: troupe's uv entry ignores its workspace members
- **WHEN** troupe's generated configuration is read
- **THEN** its `uv` entry ignores `troupe` and `troupe-*`, with no versions or update types, and its `github-actions`
  entry ignores nothing

#### Scenario: No other entry ignores anything
- **WHEN** infrastructure's and website's generated configurations are read
- **THEN** none of their entries has an `ignore`

### Requirement: A malformed ignore declaration fails the check
`scripts/check.py` SHALL fail, naming the repository and ecosystem, when the ignore declaration names a repository or
ecosystem that isn't declared for Dependabot, or gives one an empty list or the same name twice.

#### Scenario: An undeclared ecosystem
- **WHEN** the declaration names `npm` for troupe, which troupe's Dependabot ecosystems don't include
- **THEN** `scripts/check.py` fails, naming troupe and `npm`

#### Scenario: An undeclared repository
- **WHEN** the declaration names a repository that isn't declared for Dependabot
- **THEN** `scripts/check.py` fails, naming that repository

#### Scenario: An empty list
- **WHEN** the declaration gives troupe's `uv` an empty list
- **THEN** `scripts/check.py` fails, naming troupe and `uv`

#### Scenario: A repeated name
- **WHEN** the declaration names `troupe` twice in troupe's `uv` list
- **THEN** `scripts/check.py` fails, naming troupe, `uv` and `troupe`
