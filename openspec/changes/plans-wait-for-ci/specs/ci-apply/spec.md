## ADDED Requirements

### Requirement: A scheduled or manual plan of main waits for green CI
Before a scheduled or manual run plans `main`, it SHALL check CI on the commit CI runs on for `main`'s head: the newest
commit on `main` that changes more than `tofu/terraform.tfstate`, or one after it that CI ran on. It SHALL plan only
once that CI has passed, waiting while CI is pending or running, up to a time limit. No input SHALL let a run skip
this check. A run after CI on a merge SHALL be unchanged.

#### Scenario: Green CI is planned as before
- **WHEN** a scheduled or manual run starts and CI passed on `main`'s newest commit that CI runs on
- **THEN** the run plans `main`'s head, as it did before this requirement

#### Scenario: The App's state commit is looked past
- **WHEN** a scheduled run starts and `main`'s head is the App's state commit after an apply
- **THEN** the run checks CI on the commit before it, the one that was applied, and plans `main`'s head once that
  CI has passed

#### Scenario: Running CI is waited for
- **WHEN** a scheduled or manual run starts while CI on that commit is queued or running
- **THEN** the run waits, and plans once CI passes, or fails as for red CI if CI fails

#### Scenario: A manual run can't skip the check
- **WHEN** the owner starts the run by hand while CI on `main` is red
- **THEN** it fails as a scheduled run does, and the run takes no input that skips the check

#### Scenario: A run after CI on a merge is unchanged
- **WHEN** CI passes on a merge to `main` and its run starts
- **THEN** that run plans as before this requirement, without checking CI again

### Requirement: A red main fails a scheduled or manual plan, saying how to recover
When CI on that commit concluded anything but success, or didn't finish within the time limit, a scheduled or manual
run SHALL fail before planning or asking for approval. Its summary SHALL name the commit, link the CI run, and say how
to recover: a fix pull request, a re-run of the failed CI job, or a break-glass apply from the owner's machine.

#### Scenario: Red CI fails the run before planning
- **WHEN** a scheduled or manual run starts and CI failed on `main`'s newest commit that CI runs on
- **THEN** the plan job fails without planning or asking for approval, and its summary names the commit, links the
  failed CI run, and lists the three ways to recover

#### Scenario: A cancelled CI run isn't green
- **WHEN** CI on that commit was cancelled, timed out, or concluded anything else but success
- **THEN** the run fails as for red CI

#### Scenario: CI that doesn't finish in time fails the run
- **WHEN** CI on that commit hasn't finished within the time limit
- **THEN** the plan job fails without planning, saying CI didn't finish and naming the commit

#### Scenario: A red main fails every daily run until it's green
- **WHEN** CI on `main` stays red across several days
- **THEN** each daily run fails the same way, and the first daily run after CI passes plans as usual

## MODIFIED Requirements

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

#### Scenario: A red main doesn't stop the drift job
- **WHEN** a scheduled or manual run's plan fails because CI on `main` failed or is still running
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
