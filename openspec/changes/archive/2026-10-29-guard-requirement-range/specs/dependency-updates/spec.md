## MODIFIED Requirements

### Requirement: The issue says what the update is
The issue's title SHALL name the dependency and the versions it moves between. Its body SHALL link the pull request,
whose description carries Dependabot's release notes, and give the update type: patch, minor, major, or unknown when
the versions can't be read. A requirement update's ranges SHALL be counted as the `guard` check counts them. For a
major or unknown update, the body SHALL say the update needs an OpenSpec change.

#### Scenario: A patch update
- **WHEN** a run opens the issue for website's `chore(deps): Bump zod from 4.6.5 to 4.6.7`
- **THEN** its title names zod, 4.6.5 and 4.6.7, and its body links the pull request and says the update is a patch

#### Scenario: A major update
- **WHEN** a run opens the issue for `chore(deps-dev): Bump typescript from 6.0.3 to 7.0.2`
- **THEN** its body says the update is major and needs an OpenSpec change before it can merge

#### Scenario: A requirement range within a minor series
- **WHEN** a run opens the issue for troupe's `chore(deps-dev): Update uv-build requirement from <0.14,>=0.13.0 to
  >=0.13.5,<0.14`
- **THEN** its body says the update is a patch, and doesn't say it needs an OpenSpec change

#### Scenario: A requirement range that admits a new major
- **WHEN** a run opens the issue for `Update jsonschema requirement from <5,>=4.26 to >=4.26,<6`
- **THEN** its body says the update is major and needs an OpenSpec change

#### Scenario: Versions that can't be read
- **WHEN** a Dependabot pull request's title doesn't give a version it moves from and one it moves to, or gives
  ranges whose bounds don't match one for one
- **THEN** its issue is still opened, titled from the pull request's title, and its body says the update type is
  unknown and needs an OpenSpec change
