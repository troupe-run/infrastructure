## MODIFIED Requirements

### Requirement: A change runs the checks its paths need
This repository SHALL declare a scope, in its check-paths declaration, for each of its declarations that only some
tests read: DNS records, milestones, labels, the OpenTofu configuration, the docs and the out-of-band declarations
(`oob/`). A commit, and a pull request's `check` job, SHALL run what the guard's check-scope answer gives for the changed paths: nothing, those scopes, or the
full check. Every non-test gate runs in a scoped check.

#### Scenario: A DNS-only pull request
- **WHEN** a pull request changes only `tofu/dns.json` and files under `openspec/`
- **THEN** its `check` job runs `scripts/check.py --scope dns`: ruff, mypy, `tofu fmt` and `tofu validate`, and only
  the tests tagged `dns`, and the job reports success when they pass

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

### Requirement: The check runs its tests in parallel workers
This repository's check SHALL run its tests in a fixed number of parallel worker processes, set in one named place,
and never more than the machine's CPUs. A full or scoped check SHALL run the same tests it would in one process.

#### Scenario: The full check's tests
- **WHEN** `scripts/check.py` runs on a machine with at least as many CPUs as the named worker count
- **THEN** its tests run in that many worker processes

#### Scenario: A machine with fewer CPUs
- **WHEN** `scripts/check.py` runs where there are fewer CPUs than the named worker count
- **THEN** its tests run in one worker per CPU

#### Scenario: A scoped check's tests
- **WHEN** `scripts/check.py --scope dns` runs
- **THEN** the tests tagged `dns` run in parallel workers, and they are the same tests a run in one process selects
