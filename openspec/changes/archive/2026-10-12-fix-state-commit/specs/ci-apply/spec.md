# Spec Delta

## MODIFIED Requirements

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
