# Spec Delta

## Purpose

How a declared change reaches the org from CI: the plan on every pull request, and the plan, approval and apply on
`main`. Covers the environments that gate them, and the commit of the new state after an apply.

## ADDED Requirements

### Requirement: Every pull request is planned in CI
A pull request into `main` SHALL get a plan made in CI, against the state on `main`, posted on the pull request,
once the owner has approved that run. The plan is the pull request's evidence. When the pull request is updated, the posted plan SHALL be replaced rather
than added to. A pull request from a fork SHALL NOT be planned, because it gets no secrets.

#### Scenario: A pull request that changes the org shows its plan
- **WHEN** a pull request changes what is declared
- **THEN** a plan showing that change is posted on the pull request once the owner approves the run, without the
  owner running anything locally

#### Scenario: A new push replaces the plan
- **WHEN** a pull request that already has a posted plan is pushed to again
- **THEN** the pull request shows one plan: the latest

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
the infrastructure App, in one Conventional Commit that names the commit that was applied. That commit SHALL NOT
start another plan. If the commit can't be made, the run SHALL fail, and keep the encrypted state where the owner can
recover it.

#### Scenario: State follows an apply
- **WHEN** an approved apply finishes
- **THEN** `main` has a new commit by the App that changes only `tofu/terraform.tfstate`, and no plan-and-apply run
  starts for it

#### Scenario: A failed state commit isn't lost
- **WHEN** an apply succeeds but committing the state fails
- **THEN** the run fails, and the encrypted state is kept as an artifact of the run

### Requirement: CI runs can be started by hand on main
The owner SHALL be able to start a plan-and-apply run on `main` by hand, for example after drift or a rejected
approval. It follows the same plan, approval and apply.

#### Scenario: Drift is planned on demand
- **WHEN** the owner starts the run by hand after a change was made on GitHub outside OpenTofu
- **THEN** the run plans the drift's reversal and waits for approval like any other
