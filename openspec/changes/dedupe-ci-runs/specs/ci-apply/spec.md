# Spec Delta

## ADDED Requirements

### Requirement: CI tests each pull request once, and main after every push
This repository's tests (the `check` and `guard tests` jobs) SHALL run once for each update to a pull request, on the
pull request merged onto `main`, and once for every push to `main` that changes more than the state file. A push to
any other branch, and the App's state commit after an apply, SHALL NOT run them again. The `guard` check's triggers
are set by "The rules are re-checked on GitHub" (development-workflow).

#### Scenario: A pull request is tested once
- **WHEN** a commit is pushed to a branch that has an open pull request into `main`
- **THEN** each of the `check` and `guard tests` jobs reports once on that commit, from the pull request's run

#### Scenario: A merge to main is tested, and then planned
- **WHEN** a pull request is merged into `main`
- **THEN** CI tests `main`'s new head, and the plan of `main` follows that run once it passes

#### Scenario: The state commit isn't tested again
- **WHEN** the App commits the state to `main` after an apply, changing only the state file
- **THEN** CI doesn't run its tests on that commit, and the `guard` check still runs on the push

#### Scenario: A branch with no pull request
- **WHEN** a branch other than `main` is pushed and no pull request is open for it
- **THEN** CI doesn't run its tests, and the `guard` check still runs on the push
