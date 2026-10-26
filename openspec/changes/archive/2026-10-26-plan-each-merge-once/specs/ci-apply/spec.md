## ADDED Requirements

### Requirement: A plan of main reads main's current state
Every plan of `main` SHALL be made with the state on `main` when the plan starts, never an older one. A run after CI on
a merge SHALL plan the newest commit with that merge's declaration and `main`'s current state: the merge, or an App
state commit straight after it. If none has, because state was committed after a later merge, it SHALL plan nothing,
say why in its summary, and ask for no approval.

#### Scenario: A merge another run already applied asks nothing
- **WHEN** a scheduled or manual run applies a merge before CI on that merge has finished, and the merge's own run
  then starts
- **THEN** that run plans `main`'s head with the state the apply left, shows no changes, and asks for no approval

#### Scenario: Two merges in a row
- **WHEN** a second merge's run waits behind the first's approval, and the first's apply commits new state
- **THEN** the second run plans with that new state, and its plan shows only what the second merge changes

#### Scenario: An apply before a later merge doesn't hold the earlier merge up
- **WHEN** a merge's run starts after an apply has committed state and then a later merge has landed, with no state
  committed since
- **THEN** the run plans the merge's declaration with that state, whatever the later merge's CI concludes

#### Scenario: State committed after a later merge
- **WHEN** a merge's run starts after a later merge has landed and an apply has then committed state
- **THEN** the run plans nothing and asks for no approval, and its summary names the later merge whose run plans
  with the current state

#### Scenario: A merge with the current state is planned as itself
- **WHEN** a merge's run starts and the merge's state file is the one on `main`'s head, whether or not later merges
  have landed
- **THEN** the run plans that merge, as before this requirement

#### Scenario: A scheduled run that waited plans main's head
- **WHEN** a scheduled or manual run waits behind another run's apply, and the apply commits new state
- **THEN** it plans `main`'s head as it is when its plan starts, not the commit it was started on

#### Scenario: The summary names what was planned
- **WHEN** a run on `main` plans a commit other than the one it was started for
- **THEN** its summary names both commits and why the other was planned

#### Scenario: A commit that isn't on main fails the run
- **WHEN** a run after CI is for a commit that `main`'s history doesn't contain
- **THEN** the plan job fails, naming the commit, and nothing is planned or offered for approval
