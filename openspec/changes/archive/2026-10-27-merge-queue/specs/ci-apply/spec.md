## ADDED Requirements

### Requirement: CI tests the merge queue's commit in full
This repository's tests (the `check` and `guard tests` jobs) SHALL run once for each commit the merge queue tests,
in full, whatever paths the queued pull requests changed, as they do on a push to `main`.

#### Scenario: A queued pull request is tested on top of main
- **WHEN** a pull request that changes only documentation joins this repository's merge queue
- **THEN** CI runs the full check and every guard-tests leg on the queue's commit, and each reports there

### Requirement: A pull request's plan isn't run again in the merge queue
On this repository, the `plan (pull request)` check SHALL report as skipped on a merge queue's commit, asking for no
approval and holding no credential. The plan of `main` that follows the merge SHALL still be made and approved
before anything applies. A queue's run SHALL NOT wait for, or hold up, a plan or apply of `main`.

#### Scenario: A queued pull request needs no second approval
- **WHEN** a pull request whose plan the owner approved joins the merge queue
- **THEN** `plan (pull request)` reports as skipped on the queue's commit without the owner approving anything, and
  the pull request can land once the other required checks pass

#### Scenario: Main is still planned after the queue lands
- **WHEN** the queue lands a pull request that changes what is declared
- **THEN** CI on `main` is followed by `plan (main)`, and nothing applies until the owner approves it

#### Scenario: A queue run while main is being applied
- **WHEN** a pull request joins the queue while an apply of `main` is waiting for approval
- **THEN** the queue's runs proceed without waiting for that apply, and the apply isn't cancelled
