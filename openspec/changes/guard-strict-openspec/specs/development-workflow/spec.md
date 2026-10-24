## ADDED Requirements

### Requirement: Specs and active changes pass strict validation on GitHub
In a repository with an `openspec/` root, the `guard` check SHALL fail under `openspec-strict` when a main spec or an
active change in its scope doesn't pass OpenSpec's strict validation, naming each spec or change at fault, each
requirement at fault by its name, OpenSpec's message, and the fix. Archived changes aren't validated.

#### Scenario: A requirement over the length limit
- **WHEN** a pull request changes the main spec `runner-protocol`, and its requirement `Steps are reported` has a
  description over 500 characters
- **THEN** the `guard` check fails under `openspec-strict`, naming the spec `runner-protocol`, the requirement
  `Steps are reported` and OpenSpec's message
- **AND** the fix gives the command that reproduces it locally and the OpenSpec version the check ran

#### Scenario: An active change that fails strict validation
- **WHEN** a push carries a commit that changes the active change `x`, whose delta adds a requirement with no scenario
- **THEN** the `guard` check fails under `openspec-strict`, naming the change `x`, the requirement and OpenSpec's
  message

#### Scenario: Every spec and change in scope passes
- **WHEN** every main spec and active change in the check's scope passes strict validation
- **THEN** `openspec-strict` doesn't fail the `guard` check

#### Scenario: An archived change that would fail strict validation
- **WHEN** a push to `main` leaves a change under `openspec/changes/archive/` that would fail strict validation, and
  every main spec and active change passes
- **THEN** `openspec-strict` doesn't fail the `guard` check

### Requirement: A pull request is validated for what it touches
For a pull request, and a push to any branch but `main`, the scope SHALL be the main specs and active changes the
commits change. It SHALL be every main spec and active change when the commits change the guard itself, which pins the
OpenSpec version. A spec that fails but isn't in scope SHALL NOT fail the check.

#### Scenario: A pull request that touches no spec
- **WHEN** a pull request changes only files outside `openspec/` and the guard, and a main spec on its branch fails
  strict validation
- **THEN** `openspec-strict` doesn't fail the `guard` check

#### Scenario: A pull request that touches one spec while another fails
- **WHEN** a pull request changes the main spec `a`, which passes, and the main spec `b`, which it doesn't change,
  fails strict validation
- **THEN** `openspec-strict` doesn't fail the `guard` check

#### Scenario: Archiving a change that leaves a spec failing
- **WHEN** a pull request archives a change and so changes the main spec `a`, which then fails strict validation
- **THEN** the `guard` check fails under `openspec-strict`, naming the spec `a`

#### Scenario: A pull request that moves the OpenSpec version
- **WHEN** a pull request changes `.github/workflows/guard.yml` or `scripts/guard.py`, and a main spec it doesn't
  otherwise touch fails strict validation with the new version
- **THEN** the `guard` check fails under `openspec-strict`, naming that spec

### Requirement: A push to main is validated in full
For a push to `main`, including a delivery of the guard's files, the scope SHALL be every main spec and every active
change, whatever the push changed, so a spec that fails on `main` shows on `main`'s own `guard` run.

#### Scenario: A delivery that brings a stricter OpenSpec version
- **WHEN** the guard's files are delivered to `main` with an OpenSpec version under which a main spec fails strict
  validation
- **THEN** `main`'s `guard` run fails under `openspec-strict`, naming that spec

### Requirement: Strict validation that can't run fails the check
When its scope isn't empty, the `guard` check SHALL fail under `openspec-strict` if it can't run OpenSpec's strict
validation or can't read its result, saying which and how to fix it, and SHALL NOT pass a run whose result it doesn't
have. A repository with no `openspec/` root, or a run whose scope is empty, SHALL pass this rule without running
OpenSpec.

#### Scenario: The OpenSpec CLI is missing
- **WHEN** the `guard` check's scope isn't empty and no `openspec` command is installed
- **THEN** the check fails under `openspec-strict`, saying the OpenSpec CLI wasn't found and where its version is
  pinned

#### Scenario: OpenSpec's result can't be read
- **WHEN** OpenSpec exits without printing a result the guard can read
- **THEN** the check fails under `openspec-strict`, saying the result couldn't be read and giving OpenSpec's exit status
  and error output

#### Scenario: A repository without OpenSpec
- **WHEN** the `guard` check runs in a repository with no `openspec/` directory
- **THEN** `openspec-strict` doesn't fail the check, and OpenSpec isn't run
