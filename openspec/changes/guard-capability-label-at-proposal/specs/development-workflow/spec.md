## ADDED Requirements

### Requirement: A troupe spec's capability labels are checked on GitHub
In troupe-run/troupe, the `guard` check SHALL fail under `capability-label` when a spec in its scope has no
`Capability:` line as the first line of its Purpose, has one that's malformed, or names a label that
`tofu/labels/troupe.json` on troupe-run/infrastructure's `main` doesn't declare. Each failure SHALL name the spec,
the change for a proposed spec, the label, and the fix. It isn't overridable. Elsewhere the rule SHALL NOT apply.

#### Scenario: A proposed spec names a label that exists
- **WHEN** a push to troupe changes the active change `x`, whose delta adds the new spec `run-workspaces` with the
  Purpose's first line ``Capability: `cap:stages` ``, and `cap:stages` is declared on infrastructure's `main`
- **THEN** `capability-label` doesn't fail the `guard` check

#### Scenario: A proposed spec names a label that doesn't exist
- **WHEN** that delta's line is ``Capability: `cap:workspaces` ``, and `cap:workspaces` isn't declared
- **THEN** the `guard` check fails under `capability-label`, naming the change `x`, the spec `run-workspaces` and
  `cap:workspaces`
- **AND** the fix links "A capability label" in infrastructure's `docs/standard-changes.md`, says to open the label's
  sub-issue from it, and offers naming a declared label instead

#### Scenario: An edit to an existing spec's line
- **WHEN** a pull request to troupe changes the main spec `stages`'s line to ``Capability: `cap:stages`, `cap:gates` ``,
  and `cap:gates` isn't declared
- **THEN** the `guard` check fails under `capability-label`, naming the spec `stages` and `cap:gates`

#### Scenario: A proposed spec with no line
- **WHEN** a push to troupe changes an active change whose delta adds a new spec with no `## Purpose`, or with a Purpose
  whose first line isn't a `Capability:` line
- **THEN** the `guard` check fails under `capability-label`, naming the change and the spec, and saying to put the line
  at the top of the delta's `## Purpose`

#### Scenario: A malformed line
- **WHEN** a spec in scope has the first Purpose line `Capability: cap:stages`
- **THEN** the `guard` check fails under `capability-label`, naming the spec and the line, and giving the line's shape

#### Scenario: Another repository
- **WHEN** the `guard` check runs in troupe-run/infrastructure or troupe-run/website
- **THEN** `capability-label` doesn't fail the check, and no labels are read

### Requirement: The capability label check judges what the range touches
The scope SHALL be the main specs the commits change, and each delta spec in an active change the commits change
whose main spec doesn't exist at the head. On a push to `main`, and when the commits change the guard itself, it SHALL
be every main spec and every such delta. A delta for a spec that exists SHALL NOT be judged, since OpenSpec ignores its
Purpose. An empty scope SHALL pass without reading the labels.

#### Scenario: A pull request that touches no spec
- **WHEN** a pull request to troupe changes only files outside `openspec/`, and a main spec on its branch names an
  undeclared label
- **THEN** `capability-label` doesn't fail the `guard` check, and the labels aren't read

#### Scenario: A delta for a spec that exists
- **WHEN** a push to troupe changes an active change whose delta for the existing spec `stages` has a Purpose naming an
  undeclared label
- **THEN** `capability-label` doesn't fail the `guard` check for that delta

#### Scenario: A push to main
- **WHEN** the guard's files are delivered to troupe's `main`, and a main spec the delivery doesn't touch names an
  undeclared label
- **THEN** `main`'s `guard` run fails under `capability-label`, naming that spec

#### Scenario: Archiving a proposed spec
- **WHEN** a pull request to troupe archives a change, so creating the main spec `run-workspaces`, whose line names a
  declared label
- **THEN** `capability-label` judges the main spec `run-workspaces`, and doesn't fail the `guard` check

### Requirement: The capability label check fails when it can't read the labels
When its scope isn't empty, the `guard` check SHALL fail under `capability-label` if it can't read
`tofu/labels/troupe.json` from troupe-run/infrastructure's `main`, or what it reads isn't a list of labels each with a
name, saying which and how to fix it. It SHALL NOT pass a spec whose labels it couldn't check.

#### Scenario: GitHub can't be reached
- **WHEN** the scope isn't empty and the request for the labels fails or times out
- **THEN** the `guard` check fails under `capability-label`, naming the file and the reason, and saying to re-run the
  check

#### Scenario: The file isn't a list of labels
- **WHEN** the labels read back as something other than a JSON list of objects with a string `name`
- **THEN** the `guard` check fails under `capability-label`, saying the declared labels couldn't be read
