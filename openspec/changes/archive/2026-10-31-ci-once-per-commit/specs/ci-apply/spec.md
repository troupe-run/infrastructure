## RENAMED Requirements

- FROM: `### Requirement: CI tests each pull request once, and main after every push`
- TO: `### Requirement: CI tests each version of the code once`

## MODIFIED Requirements

### Requirement: CI tests each version of the code once
This repository's tests (the `check` and `guard tests` jobs) SHALL run once for each update to a ready pull request,
merged onto `main`, and in full on each commit a merge queue tests. A push to `main` that changes more than the state
file SHALL run them in full unless the queue passed that commit. A push to another branch, and the App's state
commit, SHALL NOT run them. The `guard` check's triggers are set by "The rules are re-checked on GitHub"
(development-workflow).

#### Scenario: A pull request is tested once
- **WHEN** a commit is pushed to a branch that has an open pull request into `main` that isn't a draft
- **THEN** each of the `check` and `guard tests` checks reports once on that commit, from the pull request's run

#### Scenario: A merge to main is tested, and then planned
- **WHEN** a commit reaches `main` without the merge queue having passed it
- **THEN** CI runs the full check and every guard-tests leg on `main`'s new head, whatever paths the commit changed,
  and the plan of `main` follows that run once it passes

#### Scenario: The state commit isn't tested again
- **WHEN** the App commits the state to `main` after an apply, changing only the state file
- **THEN** CI doesn't run its tests on that commit, and the `guard` check still runs on the push

#### Scenario: A branch with no pull request
- **WHEN** a branch other than `main` is pushed and no pull request is open for it
- **THEN** CI doesn't run its tests, and the `guard` check still runs on the push

## ADDED Requirements

### Requirement: A commit the merge queue passed isn't tested again on main
On a push to `main`, when CI's own merge-queue run on that exact commit succeeded, the `check` job and every
guard-tests leg SHALL be skipped, `guard tests` SHALL report success, and CI's run SHALL succeed, so the plan of
`main` follows it as after any green run. Otherwise, or when that run can't be read, they SHALL run in full, and a
read that fails SHALL NOT fail CI's run by itself.

#### Scenario: A merge through the queue
- **WHEN** the merge queue passes a group and lands its commit on `main`
- **THEN** CI's push run on that commit skips `check` and every guard-tests leg, `guard tests` reports success, the
  run succeeds, and the plan of `main` starts

#### Scenario: A commit the queue didn't pass
- **WHEN** a commit that changes more than the state file reaches `main` with no successful merge-queue run of CI on
  it
- **THEN** CI runs the full check and every guard-tests leg on it

#### Scenario: The queue's run on that commit failed
- **WHEN** CI's merge-queue run on the commit concluded anything but success
- **THEN** CI runs the full check and every guard-tests leg on it

#### Scenario: The queue's run is still finishing
- **WHEN** CI's merge-queue run on the commit hasn't completed when the push run asks
- **THEN** the push run waits for it, for a bounded time, and then decides as above; one that still hasn't completed
  runs everything

#### Scenario: The queue's run can't be read
- **WHEN** the read of CI's runs on the commit fails
- **THEN** CI runs the full check and every guard-tests leg, the run annotates the failed read as a warning, and the
  run's result is the tests' result

#### Scenario: A scheduled or manual plan after a skipped run
- **WHEN** a scheduled or manual plan of `main` waits for CI on a commit whose push run skipped its tests
- **THEN** it finds that run green and plans

### Requirement: A draft pull request isn't tested or planned until it's ready
On a draft pull request, CI's `check` job and every guard-tests leg SHALL be skipped, with `guard tests` reporting
success, and `plan (pull request)` SHALL be skipped without asking the owner for an approval. Marking the pull request
ready for review SHALL run them as any update does. A draft can't merge or join the merge queue, so what it skips
lets nothing land.

#### Scenario: A draft is opened or pushed to
- **WHEN** a draft pull request is opened, or a commit is pushed to one
- **THEN** no guard-tests leg runs, `check` and `plan (pull request)` are skipped, `guard tests` reports success, and
  the owner isn't asked to approve a plan

#### Scenario: A draft is marked ready
- **WHEN** a draft pull request is marked ready for review
- **THEN** CI runs what its changed paths need, and `plan (pull request)` asks the owner's approval when the changed
  paths need a plan

#### Scenario: A pull request goes back to draft
- **WHEN** a pull request is converted to a draft and then pushed to
- **THEN** that push's run skips the tests and the plan, as for any draft

#### Scenario: The draft check itself fails
- **WHEN** the job that decides what a pull request needs fails on a draft
- **THEN** every leg and the full check run, and the plan asks for approval, as when that job fails on any pull
  request
