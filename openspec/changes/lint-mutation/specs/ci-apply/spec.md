## MODIFIED Requirements

### Requirement: A change runs the checks its paths need
This repository SHALL declare a scope, in its check-paths declaration, for each of its declarations that only some
tests read: DNS records, milestones, labels, the OpenTofu configuration, the docs and the out-of-band declarations
(`oob/`). A commit, and a pull request's `check` job, SHALL run what the guard's check-scope answer gives for the
changed paths: nothing, those scopes, or the full check. Every non-test gate runs in a scoped check.

#### Scenario: A DNS-only pull request
- **WHEN** a pull request changes only `tofu/dns.json` and files under `openspec/`
- **THEN** its `check` job runs `scripts/check.py --scope dns`: ruff, mypy, `tofu fmt`, `tofu validate` and `tflint`, and
  only the tests tagged `dns`, and the job reports success when they pass

#### Scenario: A DNS-only commit
- **WHEN** a commit stages only `tofu/dns.json` and its change's `tasks.md`
- **THEN** the pre-commit check runs `scripts/check.py --scope dns`, and the guard says so

#### Scenario: An oob-only commit
- **WHEN** a commit stages only files under `oob/`, with or without files under `openspec/`
- **THEN** the pre-commit check runs `scripts/check.py --scope oob`, and only the tests tagged `oob` run

#### Scenario: Two declarations change
- **WHEN** a pull request changes `tofu/milestones.json` and a file under `tofu/labels/`
- **THEN** its `check` job runs `scripts/check.py --scope labels --scope milestones`

#### Scenario: Only skipped paths change
- **WHEN** a pull request changes only files under `openspec/`
- **THEN** its `check` job runs no gate and reports success

#### Scenario: Any other path changes
- **WHEN** a pull request changes a path in no scope and not skipped, such as `scripts/tofu.py`, a new top-level file
  or `scripts/check-paths.toml` itself
- **THEN** its `check` job runs the full check

#### Scenario: The changed paths can't be listed
- **WHEN** the `check` job can't list the pull request's changed paths, or the list is empty
- **THEN** it runs the full check

#### Scenario: A malformed declaration in a pull request
- **WHEN** a pull request's `scripts/check-paths.toml` is malformed
- **THEN** its `check` job fails, naming the file, what's wrong and the fix

#### Scenario: Every test that reads a changed declaration is selected
- **WHEN** a test reads a file in one of this repository's scopes
- **THEN** it carries that scope's tag, or every run of the tests fails it, naming the test, the file and the tag

## ADDED Requirements

### Requirement: The check lints the OpenTofu configuration
The check SHALL run `tflint` over the OpenTofu configuration, with its rules declared in one file in this repository,
locally and in CI's `check` job, and SHALL fail when it reports a finding. A rule turned off, or a finding accepted,
SHALL be recorded in that file with its reason.

#### Scenario: A finding fails the check
- **WHEN** a change adds a variable to `tofu/` that nothing uses
- **THEN** `scripts/check.py` fails at the `tflint` gate, naming the file, the line and the rule

#### Scenario: The configuration as it is passes
- **WHEN** the check runs on `main` after this change
- **THEN** `tflint` reports no finding

### Requirement: CI always runs tflint; a local check may go without it
CI SHALL install the `tflint` version the rules file names, and the check in GitHub Actions SHALL fail when `tflint` is
missing. A local check without `tflint` SHALL say the gate is skipped and how to install it, and run the other gates.

#### Scenario: tflint isn't installed in CI
- **WHEN** the check runs in GitHub Actions with no `tflint` on the PATH
- **THEN** it fails before any gate runs, naming `tflint`

#### Scenario: tflint isn't installed locally
- **WHEN** the check runs outside GitHub Actions with no `tflint` on the PATH
- **THEN** it prints that the `tflint` gate is skipped and the command that installs it, and runs every other gate

#### Scenario: An installed tflint that fails
- **WHEN** `tflint` is installed locally and reports a finding
- **THEN** the check fails at the `tflint` gate, as in CI

#### Scenario: CI's version drifts from the declared one
- **WHEN** the version CI installs and the version the rules file names differ
- **THEN** this repository's tests fail, naming both
