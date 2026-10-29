## MODIFIED Requirements

### Requirement: An exempt Dependabot branch is a single minor or patch update
A Dependabot branch SHALL be exempt only when every commit's subject is Dependabot's for one dependency moving from
one version to another, or updating one dependency's requirement, and its versions count as a minor or patch update:
dotted runs of digits whose first differing part is the second or a later one. Any `update-type` in a message SHALL
be `version-update:semver-minor` or `version-update:semver-patch`. A major update, or one whose versions can't be
read, SHALL NOT be exempt.

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

#### Scenario: An update type that disagrees with the versions
- **WHEN** a Dependabot commit's subject moves `1.2.3` to `1.2.4` and its message says `update-type:
  version-update:semver-major`
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: The same counting as the issue
- **WHEN** any pair of versions is counted by the check and by `dependabot-issues`
- **THEN** both call it the same kind of update

## ADDED Requirements

### Requirement: A Dependabot requirement update is read from the manifest lines it changes
For a commit whose subject updates one dependency's requirement, the GitHub check SHALL read its versions from the
lines it changes in `package.json` and `pyproject.toml`, never from its message or the pull request's title. Each
removed line SHALL pair with the added line at the same place, naming the subject's dependency, and differ from it
only in version numbers. The update's kind SHALL be the largest step any number moves, counted as a version bump is.

#### Scenario: A lower bound raised within a minor series
- **WHEN** a commit with subject `chore(deps-dev): Update uv-build requirement` changes only
  `requires = ["uv_build>=0.13.0,<0.14"]` to `requires = ["uv_build>=0.13.5,<0.14"]` in `pyproject.toml`
- **THEN** the update counts as a patch

#### Scenario: An upper bound raised a minor step
- **WHEN** a requirement update changes `"eventsourcing>=9.5.6,<9.6"` to `"eventsourcing>=9.6.0,<9.7"`, and changes
  `uv.lock`
- **THEN** the update counts as minor

#### Scenario: A range that admits a new major
- **WHEN** a requirement update changes `"jsonschema>=4.26,<5"` to `"jsonschema>=4.26,<6"`
- **THEN** the GitHub check fails on the branch-change rule, saying the update is major

#### Scenario: A bound that goes down
- **WHEN** a requirement update changes `uv_build>=0.13.5,<0.14` to `uv_build>=0.13.0,<0.14`
- **THEN** the GitHub check fails on the branch-change rule, saying the requirement's versions can't be read as a
  minor or patch update, and naming the line

#### Scenario: A line that changes more than versions
- **WHEN** a requirement update changes `uv_build>=0.13.0,<0.14` to `uv_build~=0.13.5`
- **THEN** the GitHub check fails on the branch-change rule, saying the requirement's versions can't be read, and
  naming the line

#### Scenario: A line for another dependency
- **WHEN** a commit with subject `Update uv-build requirement` also moves `"pydantic>=2.14,<3"` to
  `"pydantic>=2.15,<3"`
- **THEN** the GitHub check fails on the branch-change rule, saying the line doesn't name uv-build

#### Scenario: A requirement update that changes no manifest line
- **WHEN** a commit with subject `Update uv-build requirement` changes only `uv.lock`
- **THEN** the GitHub check fails on the branch-change rule, saying the requirement's versions can't be read

#### Scenario: The message's versions are ignored
- **WHEN** a requirement update's diff moves `0.13.0` to `0.13.5` and its message says `dependency-version: 0.13.3`
- **THEN** the update counts as a patch, read from the diff alone

#### Scenario: The same reading as the issue
- **WHEN** a requirement update's manifest line and its pull request's title give the same ranges
- **THEN** the check and `dependabot-issues` call it the same kind of update
