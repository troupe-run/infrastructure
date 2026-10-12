# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
