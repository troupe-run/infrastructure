## ADDED Requirements

### Requirement: What OpenTofu can't manage is checked whenever main is planned
Whenever CI plans `main` (daily, after CI passes on a merge, or on a manual run), it SHALL also run the drift check
for what OpenTofu can't manage, in a job that doesn't depend on the plan. The job SHALL run only on `main`, and SHALL
read GitHub with a token that can only read.

#### Scenario: The daily run checks what OpenTofu can't manage
- **WHEN** the daily run of `main`'s plan starts
- **THEN** the drift job runs too, whatever the plan's result

#### Scenario: A failed plan doesn't hide drift
- **WHEN** the plan of `main` fails
- **THEN** the drift job still runs and reports its own result

#### Scenario: Drift outside OpenTofu doesn't stop the plan
- **WHEN** the drift job finds a difference in the same run as the daily plan
- **THEN** the plan still runs and, if it has changes, still waits for the owner's approval

#### Scenario: A branch can't get the drift job's credential
- **WHEN** a workflow run on any ref other than `main`, a pull request included, asks for the drift job's credential
- **THEN** GitHub refuses the deployment, and the run gets no secret from that environment

#### Scenario: The drift job can't write
- **WHEN** the drift job's token is used for any write to GitHub
- **THEN** GitHub refuses it, because the token holds only read permissions and the workflow token only
  `contents: read`

### Requirement: The drift job fails on a difference or an unreadable check, and says what it checked
The drift job SHALL run every check the drift check has, the same checks as a hand run. It SHALL fail when the check
finds a difference, and SHALL put each difference in the run's summary and annotations. A check that can't be read
SHALL fail the job, naming the check, and SHALL never count as "no difference". The run's summary SHALL list the
checks it ran.

#### Scenario: A difference fails the daily run
- **WHEN** the daily run finds that something in `oob/` differs from GitHub, such as a repository's dependency graph
  turned off by hand
- **THEN** the drift job fails, and its summary and an error annotation name the difference

#### Scenario: Nothing differs
- **WHEN** every check matches its declaration
- **THEN** the drift job succeeds, and its summary lists the checks that ran

#### Scenario: A check that can't be read fails the run
- **WHEN** one check's read fails, for example with a 403 or a network error
- **THEN** the drift job still runs every other check, then fails, naming the check that couldn't be read

#### Scenario: CI leaves no check out
- **WHEN** the drift job runs
- **THEN** it reads everything a hand run of the drift check reads, the org's App installations included
