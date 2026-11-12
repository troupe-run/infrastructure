## MODIFIED Requirements

### Requirement: An exempt Dependabot branch is a single minor or patch update
A Dependabot branch SHALL be exempt only when every commit's subject is Dependabot's for one dependency's update (a
bump, a requirement update, or a bump that leaves out its versions) and its versions count as a minor or patch update:
dotted runs of digits whose first differing part is the second or a later. Any `update-type` in a message SHALL be
`version-update:semver-minor` or `version-update:semver-patch`. A major update, or one whose versions can't be read,
SHALL NOT be exempt.

#### Scenario: A security update with no update type
- **WHEN** a Dependabot branch in `troupe-run/website` carries `build(deps): Bump postcss-selector-parser from 6.1.4
  to 6.1.5`, whose message has no `update-type`, changing only `package-lock.json`
- **THEN** the GitHub check doesn't fail on the branch-change rule

#### Scenario: A major update
- **WHEN** a Dependabot branch carries `chore(deps-dev): Bump typescript from 6.0.3 to 7.0.2`
- **THEN** the GitHub check fails on the branch-change rule, saying the update is major

#### Scenario: A requirement range
- **WHEN** troupe's `dependabot/uv/uv-build-gte-0.13.3-and-lt-0.14` carries `chore(deps-dev): Update uv-build
  requirement`, whose only changes are `uv_build>=0.13.0,<0.14` to `uv_build>=0.13.5,<0.14` in nine `pyproject.toml`
  files
- **THEN** the GitHub check doesn't fail on the branch-change rule

#### Scenario: A subject that leaves out its versions
- **WHEN** infrastructure's `dependabot/uv/types-pyyaml-6.0.12.20261030` carries `chore(deps-dev): Bump
  types-pyyaml`, whose message's `Bumps` line and `uv.lock` both move `types-pyyaml` from `6.0.12.20260906` to
  `6.0.12.20261030`
- **THEN** the GitHub check doesn't fail on the branch-change rule

#### Scenario: Four-part versions
- **WHEN** a Dependabot update moves `6.0.12.20260906` to `6.0.12.20261030`
- **THEN** it counts as a patch, because the first part that differs is the fourth

#### Scenario: An update type that disagrees with the versions
- **WHEN** a Dependabot commit's subject moves `1.2.3` to `1.2.4` and its message says `update-type:
  version-update:semver-major`
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: The same counting as the issue
- **WHEN** any pair of versions is counted by the check and by `dependabot-issues`
- **THEN** both call it the same kind of update

## ADDED Requirements

### Requirement: A Dependabot bump whose subject leaves out its versions is read from two agreeing sources
For a commit whose subject is `Bump <dependency>` with no versions, the GitHub check SHALL read the versions from its
message's first `Bumps [<dependency>](…) from A to B.` line, from each lock file it changes, and the step from each
manifest line it changes, never from `updated-dependencies` alone. At least two readings SHALL be present and agree,
or the commit SHALL be refused, saying which readings were found and which disagree.

#### Scenario: The message and the lock file agree
- **WHEN** a commit with subject `Bump types-pyyaml` has the line `Bumps [types-pyyaml](…) from 6.0.12.20260906 to
  6.0.12.20261030.` and changes `uv.lock`'s `types-pyyaml` version between the same two versions
- **THEN** the update counts as a patch

#### Scenario: The message and the lock file disagree
- **WHEN** a commit with subject `Bump zod` says `Bumps [zod](…) from 4.6.5 to 4.6.7.` and changes
  `package-lock.json`'s `zod` from `4.6.5` to `4.7.0`
- **THEN** the GitHub check fails on the branch-change rule, naming both readings' versions

#### Scenario: Only one reading
- **WHEN** a commit with subject `Bump zod` has no `Bumps` line and changes only `package-lock.json`
- **THEN** the GitHub check fails on the branch-change rule, saying only one reading was found where two must agree

#### Scenario: A major update read from two sources
- **WHEN** a commit with subject `Bump typescript` says `from 6.0.3 to 7.0.2` and `package-lock.json` agrees
- **THEN** the GitHub check fails on the branch-change rule, saying the update is major

#### Scenario: A manifest line that moves by another kind of step
- **WHEN** a commit with subject `Bump eventsourcing` says `from 9.5.5 to 9.5.6`, `uv.lock` agrees, and
  `pyproject.toml` moves `eventsourcing>=9.5,<9.6` to `eventsourcing>=9.6,<9.7`
- **THEN** the GitHub check fails on the branch-change rule, naming the manifest's kind and the versions' kind

#### Scenario: A lock file that can't be read
- **WHEN** a commit with subject `Bump zod` changes `package-lock.json` so that two of `zod`'s versions move
- **THEN** the GitHub check fails on the branch-change rule, naming the file

#### Scenario: The metadata alone isn't a reading
- **WHEN** a commit with subject `Bump zod` has no `Bumps` line, changes only `package-lock.json`, and its metadata
  says `dependency-version: 4.6.7` and `update-type: version-update:semver-patch`
- **THEN** the GitHub check fails on the branch-change rule, saying only one reading was found

#### Scenario: A subject that gives its versions is read as before
- **WHEN** a commit's subject is `Bump zod from 4.6.5 to 4.6.7`, whatever its `Bumps` line and lock files say
- **THEN** its kind is read from the subject alone, as before this change
