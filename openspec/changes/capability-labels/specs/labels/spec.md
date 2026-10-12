# Spec Delta

## ADDED Requirements

### Requirement: troupe's capability labels are declared here
troupe's `cap:*` labels SHALL be declared in this repository and SHALL change only by a pull request here. troupe
keeps no separate capability list: a new capability gets its label by a pull request that adds it to the
declaration, and the label is created when the owner approves the plan.

#### Scenario: A new capability gets a label
- **WHEN** a pull request adds `cap:<name>` to troupe's declared labels and a plan runs
- **THEN** the plan shows `cap:<name>` being created on troupe-run/troupe, with the declared colour and description,
  and no other label changing

#### Scenario: A capability label made by hand
- **WHEN** someone creates a `cap:*` label on troupe-run/troupe on GitHub without declaring it
- **THEN** the next plan shows that label being removed

### Requirement: A capability label in use is never removed or renamed
A `cap:*` label that any troupe issue or pull request carries, open or closed, SHALL NOT be removed from the
declaration or renamed, because removing the declared label deletes it from GitHub and takes it off every issue
that carries it, and a rename is a removal and a creation.

#### Scenario: Removing a label that issues carry
- **WHEN** a pull request removes or renames a declared `cap:*` label
- **THEN** its description lists the troupe issues and pull requests that carry the label, read from GitHub when
  the pull request is opened, and it isn't merged while that list is not empty

### Requirement: A troupe spec with no capability label is reported
The out-of-band drift check SHALL report each folder in troupe's `openspec/specs/` on `main` that has no declared
`cap:<folder>` label, naming the folder and where to add the label. A declared label with no spec SHALL NOT be
reported, since a label can come before its spec.

#### Scenario: A spec without a label
- **WHEN** troupe's `openspec/specs/` holds `artifact-store` and troupe's declared labels have no
  `cap:artifact-store`
- **THEN** the drift check prints a difference naming `artifact-store` and `tofu/labels/troupe.json`, and exits 1

#### Scenario: A label ahead of its spec
- **WHEN** troupe's declared labels include `cap:cues` and troupe has no `openspec/specs/cues/`
- **THEN** the drift check reports nothing about `cues`

#### Scenario: Every spec has a label
- **WHEN** every folder in troupe's `openspec/specs/` has a matching declared label
- **THEN** the drift check reports no difference for troupe's specs
