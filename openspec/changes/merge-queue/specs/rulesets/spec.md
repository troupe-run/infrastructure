## ADDED Requirements

### Requirement: Pull requests reach main through a merge queue
In a repository whose queue is turned on, a pull request into `main` SHALL merge only through a merge queue that
merges by rebase. The queue SHALL land exactly the commits it tested, so `main` stays linear and carries each commit.
The infrastructure App's direct pushes to `main` and the owner's pull-request bypass SHALL work as before.

#### Scenario: The owner's merge adds the pull request to the queue
- **WHEN** the owner merges a pull request into `main` whose required checks have passed, in a repository whose
  queue is on
- **THEN** the pull request joins the merge queue, and lands on `main` by rebase only after the queue's checks pass

#### Scenario: What lands is what was tested
- **WHEN** the queue lands a pull request
- **THEN** `main`'s new head is the commit the queue's checks ran on, and `main`'s history has no merge commit

#### Scenario: The App still delivers straight to main
- **WHEN** the infrastructure App pushes a delivery or a state commit to `main` in a repository whose queue is on
- **THEN** GitHub accepts the push without the queue

#### Scenario: The owner still merges past a failing check
- **WHEN** a pull request's required check has failed and an org owner merges it, choosing to bypass the rules
- **THEN** the merge succeeds without the queue

### Requirement: The queue lands only a combination whose required checks passed
A queued pull request SHALL land only when every check its repository requires has passed on the queue's commit:
`main` with the pull requests ahead of it in the queue and its own commits applied. A check that fails, or doesn't
report before the queue's timeout, SHALL remove the pull request from the queue and leave `main` unchanged.

#### Scenario: Two pull requests that break main together
- **WHEN** two pull requests each pass their checks alone, are queued one after the other, and the second fails a
  required check on top of the first
- **THEN** the first lands, the second is removed from the queue, and `main` never holds the failing combination

#### Scenario: A check that never reports
- **WHEN** a required check doesn't report on a queued commit within the queue's timeout
- **THEN** the pull request is removed from the queue and `main` is unchanged

### Requirement: A repository's queue is on only when its required checks report on the queue
Whether a repository's `main` merges through a queue SHALL be declared once per repository. A queue SHALL be turned
on only when every check that repository requires runs on merge groups, so the queue never waits on a check that
can't report.

#### Scenario: A required workflow without the queue's trigger
- **WHEN** this repository's tests run and infrastructure's queue is declared on while a workflow defining one of
  its required checks doesn't run on merge groups
- **THEN** the tests fail, naming the check and its workflow

#### Scenario: A repository with its queue off
- **WHEN** a repository's queue is declared off
- **THEN** its `main` ruleset has no merge queue rule, and its pull requests merge by rebase as before
