## MODIFIED Requirements

### Requirement: A troupe spec with no capability label is reported
The out-of-band drift check SHALL read the capability labels that each spec in troupe's `openspec/specs/` on `main`
names in the first non-blank line of its `## Purpose`. It SHALL report a spec that names no label, and a label it
names that isn't declared in `tofu/labels/troupe.json`, naming the spec. A declared label that no spec names SHALL
NOT be reported, since a label can come before its spec.

#### Scenario: A spec without a label
- **WHEN** the first non-blank line of the Purpose of troupe's `cli` spec isn't a `Capability:` line
- **THEN** the drift check prints a difference naming `cli` and saying it names no capability label, and exits 1

#### Scenario: A spec that names an undeclared label
- **WHEN** troupe's `flake-hunt` spec names `cap:development` and troupe's declared labels have no
  `cap:development`
- **THEN** the drift check prints a difference naming `flake-hunt`, `cap:development` and `tofu/labels/troupe.json`,
  and exits 1

#### Scenario: A spec that names two labels
- **WHEN** troupe's `runner-protocol` spec names `cap:actor-runners` and `cap:protocol`, and both are declared
- **THEN** the drift check reports nothing about `runner-protocol`'s labels

#### Scenario: A label ahead of its spec
- **WHEN** troupe's declared labels include `cap:cues` and no troupe spec names it
- **THEN** the drift check reports nothing about `cap:cues`

#### Scenario: A folder without a label of its own name
- **WHEN** troupe's `artifact-store` spec names `cap:storage`, which is declared, and no `cap:artifact-store` is
  declared
- **THEN** the drift check reports nothing about `artifact-store`'s labels

#### Scenario: Every spec has a label
- **WHEN** every spec in troupe's `openspec/specs/` names at least one label, and every label named is declared
- **THEN** the drift check reports no difference for troupe's specs

### Requirement: A description written from a spec records that spec's Purpose
Each spec in troupe's `openspec/specs/` on `main` SHALL have its Purpose recorded in this repository by spec, next to
the other out-of-band declarations, verbatim without its `Capability:` line. A capability label's description SHALL
be written from the Purposes of every spec that names the label.

#### Scenario: A labelled spec with no recorded Purpose
- **WHEN** troupe's `openspec/specs/` on `main` holds `<name>` and no Purpose is recorded for `<name>`
- **THEN** the drift check prints a difference naming `<name>` and the labels it names, saying its Purpose hasn't
  been recorded, and exits 1

#### Scenario: A recorded Purpose with no spec
- **WHEN** a Purpose is recorded for `cues` and troupe has no `openspec/specs/cues/`
- **THEN** the drift check prints a difference naming `cues` and the record, and exits 1

### Requirement: A description that may be stale is reported
The out-of-band drift check SHALL report each troupe spec whose Purpose on `main`, without its `Capability:` line,
differs from the Purpose recorded for it, naming the spec, the labels it names, and where to update the descriptions
and the record. Differences in line wrapping or surrounding whitespace, and changes to the `Capability:` line alone,
SHALL NOT count as a change.

#### Scenario: troupe rewrites a spec's Purpose
- **WHEN** the Purpose of troupe's `runner-protocol` spec on `main` differs from the Purpose recorded for it
- **THEN** the drift check prints a difference naming `runner-protocol`, `cap:actor-runners`, `cap:protocol`,
  `tofu/labels/troupe.json` and the record, and exits 1

#### Scenario: troupe only re-wraps a Purpose
- **WHEN** the Purpose of troupe's `runs` spec differs from the recorded one only in line breaks or spacing
- **THEN** the drift check reports nothing about `runs`' Purpose

#### Scenario: troupe changes only the labels a spec names
- **WHEN** troupe's `config-files` spec's `Capability:` line changes and the rest of its Purpose doesn't
- **THEN** the drift check reports nothing about `config-files`' Purpose

#### Scenario: Every recorded Purpose matches
- **WHEN** every troupe spec's Purpose, without its `Capability:` line, matches the Purpose recorded for it
- **THEN** the drift check reports no difference for troupe's Purposes

## ADDED Requirements

### Requirement: A malformed Capability line is reported
A first Purpose line that begins with `Capability` but isn't `Capability: ` followed by one or more distinct labels,
each in backticks and separated by `, `, with nothing after the last, SHALL be reported by the out-of-band drift
check as malformed. The report SHALL name the spec, quote the line and give the expected shape. It SHALL never be
read as naming no label, or as naming the labels it seems to.

#### Scenario: Labels without backticks
- **WHEN** the first line of troupe's `stages` spec's Purpose is `Capability: cap:stages`
- **THEN** the drift check prints a difference naming `stages`, quoting the line and giving the expected shape, and
  exits 1

#### Scenario: Text after the last label
- **WHEN** the first line of a spec's Purpose is ``Capability: `cap:vcs` (and git)``
- **THEN** the drift check reports it as malformed, and doesn't check `cap:vcs` against the declared labels

#### Scenario: A label named twice
- **WHEN** the first line of a spec's Purpose is ``Capability: `cap:vcs`, `cap:vcs` ``
- **THEN** the drift check reports it as malformed
