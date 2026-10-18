## ADDED Requirements

### Requirement: A scope can tag whole test directories
A scope in the declaration MAY list the test directories it runs, as a `tests` list of `dir/**` entries. Every test
whose file is under one of them SHALL count as tagged with that scope, for selecting a scope's tests and for the tag
check alike, as if the tag were written on the test. A malformed `tests` list SHALL be a malformed declaration.

#### Scenario: A scope's tests directories are selected
- **WHEN** scope `vcs_git` declares `tests = ["packages/vcs-git/tests/**", "packages/core/tests/**"]`, and
  `scripts/check.py --scope vcs_git` runs
- **THEN** the tests that run are exactly those under the two directories, plus any test tagged `vcs_git` in its
  source

#### Scenario: Tests run in parallel
- **WHEN** the same scoped run's tests are spread across several worker processes
- **THEN** the same tests run as in a run in one process

#### Scenario: A directory tag covers what its tests read
- **WHEN** scope `docs` covers `docs/**` and declares `tests = ["tests/docs/**"]`, and an untagged test under
  `tests/docs/` reads `docs/runs.md`
- **THEN** the tag check doesn't fail it

#### Scenario: Two scopes list the same directory
- **WHEN** scopes `blah` and `blech` both list `tests/shared/**`
- **THEN** each test under `tests/shared/` counts as tagged with both, and runs for either scope

#### Scenario: A malformed tests entry
- **WHEN** a scope's `tests` is not a list, is an empty list, or holds an entry that is not a directory written
  `dir/**` by the rules for `paths` entries, or the skip list has a `tests` key
- **THEN** the declaration is malformed, and the message names the file, the scope, the entry and how to fix it

#### Scenario: A declaration without tests keys
- **WHEN** no scope declares `tests`
- **THEN** a test counts as tagged with a scope only when its source says so, as before

### Requirement: A tests entry that matches no test fails the run
When a test run collects from a directory that contains a scope's `tests` entry, and no collected test is under that
entry, the run SHALL fail with a failure that names the scope, the entry and the fix. The scope's own run SHALL fail
too, so it can't pass by running nothing.

#### Scenario: A renamed test directory
- **WHEN** scope `vcs_git` lists `packages/vcs-git/tests/**`, that directory was renamed, and the full test run runs
- **THEN** the run fails, naming `vcs_git`, `packages/vcs-git/tests/**` and `scripts/check-paths.toml`, and saying
  to correct or remove the entry

#### Scenario: The broken scope's own run
- **WHEN** the same declaration is in place and `scripts/check.py --scope vcs_git` runs
- **THEN** the check fails for the same reason, rather than passing because nothing was selected

#### Scenario: Tests run in parallel
- **WHEN** the same run's tests are spread across several worker processes
- **THEN** it fails with the same message

#### Scenario: A narrower run
- **WHEN** a contributor runs only one test file or directory, and a scope's `tests` entry lies outside it
- **THEN** that entry isn't checked, and the run doesn't fail for it
