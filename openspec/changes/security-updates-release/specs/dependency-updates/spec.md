# Spec Delta

## ADDED Requirements

### Requirement: A shipped runtime dependency's security update releases a fix
A Dependabot pull request SHALL get release-please's commit override in its description when it counts as a security
update, its title starts `chore(deps):`, and its ecosystem is declared as shipping in its repository. The override
SHALL read the pull request's title with `chore(deps):` replaced by `fix(deps):`. Every other pull request SHALL get
none, so it releases nothing on its own.

#### Scenario: A security update to a runtime dependency in troupe
- **WHEN** troupe has an open alert for uv's `eventsourcing` first patched in `9.5.6`, and Dependabot opens
  `chore(deps): Bump eventsourcing from 9.5.5 to 9.5.6`
- **THEN** after the next run its description holds an override block reading
  `fix(deps): Bump eventsourcing from 9.5.5 to 9.5.6`, as well as its closing line

#### Scenario: A version update in troupe
- **WHEN** Dependabot opens `chore(deps): Bump eventsourcing from 9.5.5 to 9.5.6` in troupe, and troupe has no open
  alert for it
- **THEN** its description gets its closing line and no override

#### Scenario: A security update to a development dependency
- **WHEN** troupe has an open alert for uv's `pytest`, and Dependabot opens `chore(deps-dev): Bump pytest from 9.1.0 to
  9.1.1`
- **THEN** its description gets no override, and its issue is still in the release in progress

#### Scenario: A security update in an ecosystem that doesn't ship
- **WHEN** a security update opens from troupe's `github-actions` entry, or from website or infrastructure
- **THEN** its description gets no override

#### Scenario: Dependabot rewrites the description
- **WHEN** Dependabot rebases a security update that had its override, and rewrites its description without it
- **THEN** the next run puts the override back

#### Scenario: The release pull request
- **WHEN** a security update with its override and a version update both merge by rebase into troupe's `main` through
  the merge queue, while troupe is at `0.1.0`
- **THEN** troupe's release pull request lists the security update under bug fixes and releases `0.1.1`, and doesn't
  list the version update

#### Scenario: A change outside every shipped package
- **WHEN** a pull request with an override changes only files outside troupe's release-please package paths, such as
  the root `uv.lock`
- **THEN** it releases nothing

### Requirement: The ecosystems whose runtime dependencies ship are declared once
Which repositories' Dependabot ecosystems ship in a release SHALL be declared in one place in this repository.
`scripts/check.py` SHALL fail when the declaration names a repository or ecosystem that isn't declared for Dependabot,
naming it. The declaration SHALL NOT change any generated Dependabot configuration.

#### Scenario: troupe's Python packages ship
- **WHEN** the declaration is read
- **THEN** it names troupe's `uv` ecosystem, and nothing else

#### Scenario: An undeclared ecosystem
- **WHEN** the declaration names `npm` for troupe, which troupe's Dependabot ecosystems don't include
- **THEN** `scripts/check.py` fails, naming troupe and `npm`

#### Scenario: The generated files don't change
- **WHEN** the generated configurations are read after the declaration is added
- **THEN** each is the same as before

### Requirement: A run never takes an override away
A run SHALL add an override only to an open pull request that's due one, and SHALL NOT remove or change an override
already in a description, whoever wrote it. A pull request that stops counting as a security update keeps its override
until someone removes it by hand.

#### Scenario: The alert is dismissed before the merge
- **WHEN** a security update has its override, and the owner dismisses its alert before merging it
- **THEN** the next run leaves the override in the description

#### Scenario: An override removed by hand from a version update
- **WHEN** someone removes the override from a pull request that no longer counts as a security update
- **THEN** the next run doesn't put it back

## MODIFIED Requirements

### Requirement: A missed event is reported
Every run, whatever started it, SHALL count as missed each open Dependabot pull request that, when the run starts,
lacks its issue, closing line or due override and was last updated over an hour ago. It SHALL fix each one, then
report the misses in one tracking issue in infrastructure, and fail. No other work it does SHALL count as a miss.

#### Scenario: A dispatch didn't happen
- **WHEN** a run finds a website pull request rebased three hours ago with no closing line
- **THEN** it puts the line back, opens or comments on the tracking issue naming the pull request, and the run fails

#### Scenario: An override missing for hours
- **WHEN** a run finds a troupe security update rebased three hours ago with its closing line but no override
- **THEN** it puts the override back, reports the pull request in the tracking issue, and the run fails

#### Scenario: Work only time or a person makes due
- **WHEN** a run's only work is closing issues whose pull requests closed over an hour ago, or merged
- **THEN** it does that work, reports no miss, and the run succeeds

#### Scenario: A pull request updated within the hour
- **WHEN** a run finds a pull request without its closing line that Dependabot rewrote 10 minutes ago
- **THEN** it puts the line back and doesn't count it as a miss

#### Scenario: The run Dependabot's change started
- **WHEN** a run started by a "Dependabot Updates" run, or by its dispatch, finds the pull request Dependabot just
  opened or rewrote without its issue or line
- **THEN** it fixes it and doesn't count it as a miss, since the pull request changed within the hour

#### Scenario: The schedule's run is replaced in the queue
- **WHEN** the daily run is waiting behind a run in progress, and a newer run replaces it in the queue
- **THEN** the newer run counts and reports misses as the daily run would have
