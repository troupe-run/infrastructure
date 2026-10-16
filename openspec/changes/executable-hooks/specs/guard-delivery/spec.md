# Spec Delta

## ADDED Requirements

### Requirement: A delivered file has its source's mode
Each delivered file SHALL have its source's file mode in every governed repository, so a hook that is executable here
is executable there. A difference SHALL appear in the plan as a pending change, for the owner's approval like any
other. After the approved apply, the infrastructure App SHALL set the mode on `main` in a Conventional Commit naming
each file. A plan with no difference SHALL set nothing.

#### Scenario: A hook delivered without its mode shows in the plan
- **WHEN** `main` is planned while `website` holds `.githooks/pre-push` as non-executable and its source is executable
- **THEN** the plan names `website` and `.githooks/pre-push` as a mode to set, and the run waits for the owner's
  approval even when OpenTofu has no other change

#### Scenario: The approved apply sets the mode
- **WHEN** the owner approves that plan and the apply succeeds
- **THEN** `website`'s `main` gains one commit by the App, a Conventional Commit naming each file whose mode it set,
  and each of those files now has its source's mode with unchanged content

#### Scenario: A repository newly added to the targets gets executable hooks
- **WHEN** an apply delivers the guard to a repository for the first time
- **THEN** after that apply, its delivered hooks are executable, without a second plan

#### Scenario: Modes that already match set nothing
- **WHEN** a plan runs and every delivered file in every target has its source's mode
- **THEN** the plan shows no mode to set, and no governed repository gets a commit for modes

#### Scenario: A mode changed in a governed repository shows within a day
- **WHEN** a delivered hook in `troupe` stops being executable on `main` by any route
- **THEN** the daily plan shows the mode to set, and applying it restores the source's mode

#### Scenario: A file changed since the plan isn't touched
- **WHEN** a delivered file's content in a target differs at apply time from what the plan read
- **THEN** its mode isn't set, the apply's run fails naming the repository and the file, and the next plan reads it
  again
