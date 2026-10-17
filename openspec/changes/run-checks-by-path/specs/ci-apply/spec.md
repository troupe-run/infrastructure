## ADDED Requirements

### Requirement: A change runs the checks its paths need
This repository SHALL declare a scope, in its check-paths declaration, for each of its declarations that only some
tests read: DNS records, milestones, labels, the OpenTofu configuration and the docs. A commit, and a pull request's
`check` job, SHALL run what the guard's check-scope answer gives for the changed paths: nothing, those scopes, or the
full check. Every non-test gate runs in a scoped check.

#### Scenario: A DNS-only pull request
- **WHEN** a pull request changes only `tofu/dns.json` and files under `openspec/`
- **THEN** its `check` job runs `scripts/check.py --scope dns`: ruff, mypy, `tofu fmt` and `tofu validate`, and only
  the tests tagged `dns`, and the job reports success when they pass

#### Scenario: A DNS-only commit
- **WHEN** a commit stages only `tofu/dns.json` and its change's `tasks.md`
- **THEN** the pre-commit check runs `scripts/check.py --scope dns`, and the guard says so

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

### Requirement: The guard's tests run on every OS only when what they test changes
On a pull request, the guard's tests on each supported OS and Python version SHALL run when it changes a path they
depend on: a file the guard delivers, the guard's tests and their shared fixtures, the check-paths declaration, the
Python project's files, or the CI workflow. Otherwise they SHALL be skipped. One required `guard tests` check SHALL
report their result either way.

#### Scenario: A pull request that changes the guard
- **WHEN** a pull request changes `scripts/guard.py`, a file under `.githooks/`, or a `test_guard_*.py` test
- **THEN** every guard-tests leg runs, and `guard tests` passes only if every leg passed

#### Scenario: A pull request that doesn't
- **WHEN** a pull request changes only `tofu/dns.json`, `scripts/tofu.py` and files under `openspec/`
- **THEN** no guard-tests leg runs, and `guard tests` reports success

#### Scenario: A failing or cancelled leg
- **WHEN** a guard-tests leg fails or is cancelled on a pull request that needs them
- **THEN** `guard tests` fails, naming the result

#### Scenario: The decision itself fails
- **WHEN** the job that decides whether the guard's tests are needed fails
- **THEN** every leg runs, as if they were needed

#### Scenario: A delivered guard file isn't in the list
- **WHEN** the guard delivers a file that the list of paths the guard's tests depend on doesn't cover
- **THEN** this repository's tests fail, naming the file

## MODIFIED Requirements

### Requirement: CI tests each pull request once, and main after every push
This repository's tests (the `check` and `guard tests` jobs) SHALL run once for each update to a pull request, on the
pull request merged onto `main`, and once for every push to `main` that changes more than the state file. A push to
any other branch, and the App's state commit after an apply, SHALL NOT run them again. On a pull request they run what
its paths need; on `main` they SHALL run the full check and every guard-tests leg. The `guard` check's triggers are
set by "The rules are re-checked on GitHub" (development-workflow).

#### Scenario: A pull request is tested once
- **WHEN** a commit is pushed to a branch that has an open pull request into `main`
- **THEN** each of the `check` and `guard tests` checks reports once on that commit, from the pull request's run

#### Scenario: A merge to main is tested, and then planned
- **WHEN** a pull request is merged into `main`
- **THEN** CI runs the full check and every guard-tests leg on `main`'s new head, whatever paths the merge changed,
  and the plan of `main` follows that run once it passes

#### Scenario: The state commit isn't tested again
- **WHEN** the App commits the state to `main` after an apply, changing only the state file
- **THEN** CI doesn't run its tests on that commit, and the `guard` check still runs on the push

#### Scenario: A branch with no pull request
- **WHEN** a branch other than `main` is pushed and no pull request is open for it
- **THEN** CI doesn't run its tests, and the `guard` check still runs on the push
