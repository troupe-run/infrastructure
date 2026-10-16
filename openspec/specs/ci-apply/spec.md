# ci-apply Specification

## Purpose

How a declared change reaches the org from CI: the plan on every pull request, and the plan, approval and apply on
`main`. Covers the environments that gate them, and the commit of the new state after an apply.

## Requirements

### Requirement: Every pull request is planned in CI
A pull request into `main` SHALL get a plan made in CI, against the state on `main`, posted on the pull request,
once the owner has approved that run. The plan is the pull request's evidence. When the pull request is updated, the posted plan SHALL be replaced rather
than added to. A pull request from a fork SHALL NOT be planned, because it gets no secrets. A pull request that
changes only files OpenTofu never reads SHALL NOT be planned, and SHALL NOT ask the owner for an approval.

#### Scenario: A pull request that changes the org shows its plan
- **WHEN** a pull request changes what is declared
- **THEN** a plan showing that change is posted on the pull request once the owner approves the run, without the
  owner running anything locally

#### Scenario: A new push replaces the plan
- **WHEN** a pull request that already has a posted plan is pushed to again
- **THEN** the pull request shows one plan: the latest

#### Scenario: A pull request that changes only documentation isn't planned
- **WHEN** a pull request changes only files OpenTofu never reads, such as OpenSpec artifacts or `docs/`
- **THEN** its plan job is skipped, no approval is requested, and the skipped job counts as passed

#### Scenario: A change to a delivered file is planned
- **WHEN** a pull request changes only a file this repository delivers elsewhere, such as `scripts/guard.py`
- **THEN** it is planned like any other, and its plan shows the delivery

### Requirement: A pull request's run holds no credential without the owner's approval
A workflow run for a pull request SHALL NOT get any credential (the App's key or the state passphrase) until the
owner has approved that run. A run that isn't approved SHALL NOT plan. A pull request's run SHALL NOT be able to
reach the credential for planning `main`, which needs no approval.

#### Scenario: An unapproved pull request run gets nothing
- **WHEN** a pull request is pushed and the owner hasn't approved its plan run
- **THEN** the run waits, and no step in it has received a secret

#### Scenario: A pull request can't borrow main's plan credential
- **WHEN** a pull request's run asks for the environment that plans `main`
- **THEN** GitHub refuses the deployment

### Requirement: Main is applied only after the owner approves its plan
After every push to `main`, CI SHALL plan and show the plan before asking for approval. It SHALL then wait for the
owner's approval, and apply exactly the saved plan the owner saw. A plan with no changes SHALL end the run without
asking for approval. Only the owner SHALL be able to approve. Rejecting it, or not approving it, SHALL leave the org
unchanged.

#### Scenario: An approved plan is applied
- **WHEN** a merge to `main` changes what is declared and the owner approves the plan shown in the run
- **THEN** that saved plan, and nothing else, is applied

#### Scenario: A rejected plan changes nothing
- **WHEN** the owner rejects the approval
- **THEN** nothing is applied, and the change stays pending until a later run is approved

#### Scenario: Nothing to apply asks nothing
- **WHEN** a push to `main` leaves the declaration and the org in agreement
- **THEN** the run ends after the plan, with no approval requested

### Requirement: Only main can apply
An apply SHALL run only on `main`, after the owner's approval. The credential that can change the org SHALL reach a
workflow run only when the run is on `main` or the owner has approved it. A run on any other branch SHALL NOT reach
the environments that `main` uses.

#### Scenario: A branch can't apply
- **WHEN** a workflow run on a branch other than `main` asks for the apply environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from that environment

### Requirement: Applies don't overlap
At most one of CI's plan-and-apply runs on `main` SHALL be in progress at a time. A later run SHALL wait for the
earlier one to finish. An apply SHALL refuse a saved plan whose state has changed since the plan was made.

#### Scenario: Two merges in a row
- **WHEN** a second merge lands while the first run is waiting for approval
- **THEN** the second run starts after the first has finished, and plans against the state the first left

### Requirement: The new state reaches main after every apply
After an apply, whether it succeeded or failed part way, CI SHALL commit the resulting encrypted state to `main` as
the infrastructure App, in one Conventional Commit that names the commit that was applied, whatever the state's
size. That commit SHALL NOT start another plan. If the commit can't be made, the run SHALL fail, and keep the
encrypted state where the owner can recover it.

#### Scenario: State follows an apply
- **WHEN** an approved apply finishes
- **THEN** `main` has a new commit by the App that changes only `tofu/terraform.tfstate`, and no plan-and-apply run
  starts for it

#### Scenario: A large state is committed
- **WHEN** an approved apply finishes and the state is larger than an operating system allows in one command-line
  argument (128 KB on Linux)
- **THEN** the state is committed to `main` like any other

#### Scenario: A failed state commit isn't lost
- **WHEN** an apply succeeds but committing the state fails
- **THEN** the run fails, and the encrypted state is kept as an artifact of the run

### Requirement: CI runs can be started by hand on main
The owner SHALL be able to start a plan-and-apply run on `main` by hand, for example after drift or a rejected
approval. It follows the same plan, approval and apply.

#### Scenario: Drift is planned on demand
- **WHEN** the owner starts the run by hand after a change was made on GitHub outside OpenTofu
- **THEN** the run plans the drift's reversal and waits for approval like any other

### Requirement: Main is planned every day
CI SHALL plan `main` once a day, whether or not anything merged. The plan SHALL be shown, and a plan with changes
SHALL wait for the owner's approval and apply as any plan of `main` does. A plan with no changes SHALL end the run
without asking for approval. The daily plan SHALL run whatever commit `main`'s head is, the App's state commit
included.

#### Scenario: Drift shows within a day
- **WHEN** a managed file or setting is changed on GitHub outside a delivery or an apply, and nothing merges
  afterwards
- **THEN** within a day, a run on `main` shows a plan restoring it and waits for the owner's approval

#### Scenario: The state commit is planned too
- **WHEN** the daily plan runs and `main`'s head is the App's state commit after an apply
- **THEN** the run plans `main` rather than skipping

#### Scenario: No drift asks nothing
- **WHEN** the daily plan finds the declaration and the org in agreement
- **THEN** the run ends after the plan, with no approval requested

### Requirement: A pull request merges only after its plan succeeds
On this repository, a pull request's plan SHALL be a required check. A pull request that is planned SHALL NOT be
mergeable until the owner has approved its plan run and the plan has succeeded. When unsure whether a file is read
by OpenTofu, it SHALL count as read, so a mistake costs an approval rather than a missing plan.

#### Scenario: A pull request waits for its plan
- **WHEN** a pull request changes what is declared and the owner hasn't approved its plan run
- **THEN** GitHub refuses to merge it, naming the plan check

#### Scenario: A failed plan blocks the merge
- **WHEN** a pull request's plan fails, for example because the configuration doesn't plan
- **THEN** GitHub refuses to merge it

#### Scenario: A file not known to be ignored is planned
- **WHEN** a pull request changes a file outside the paths known to be ignored by OpenTofu, such as a new top-level
  directory
- **THEN** the pull request is planned

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
