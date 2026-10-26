# Spec Delta

## ADDED Requirements

### Requirement: An approved apply gives the board's options their labels' descriptions
Each option of the troupe roadmap board's `Capability` field SHALL have its `cap:<option>` label's description, as
declared here. The plan of `main` SHALL list each option whose description differs, and wait for the owner's approval
even when OpenTofu has no change. After the approved apply, the descriptions SHALL be set, changing no option's
identity, name, colour or order. An option with no label SHALL keep its description.

#### Scenario: A description that differs shows in the plan
- **WHEN** `main` is planned while the `runs` option's description is empty and `cap:runs` has a description
- **THEN** the plan's summary names `runs`, its description now and the one it will get, and the run waits for the
  owner's approval

#### Scenario: The approved apply sets it and keeps every card's value
- **WHEN** the owner approves that plan and the apply succeeds
- **THEN** the `runs` option has `cap:runs`'s description, keeps its id, name and colour, and every card that had a
  `Capability` value has the same value afterwards

#### Scenario: Descriptions that already match change nothing
- **WHEN** every option with a label already has its label's description
- **THEN** the plan lists no description to set, and nothing is sent to the board

#### Scenario: An option with no label is left alone
- **WHEN** the field has a `lifecycle` option and no `cap:lifecycle` is declared
- **THEN** the apply sends `lifecycle` back unchanged, and the drift check reports it as an option with no label

### Requirement: The board's options are never sent without their identity
Setting the descriptions SHALL send every existing option with its id, and SHALL refuse, sending nothing, when any
option to be sent has no id, or when the field's options differ from those the approved plan was made from. The
refusal SHALL name the option or the difference. Setting the descriptions SHALL never create or remove an option.

#### Scenario: An option without its id is refused
- **WHEN** an option to be sent has no id
- **THEN** nothing is sent, and the job fails naming the option

#### Scenario: The field changed since the plan
- **WHEN** the owner adds, removes or renames an option, or edits a description, between the plan and the apply
- **THEN** nothing is sent, the job fails naming what changed, and the next plan of `main` lists the descriptions
  again

#### Scenario: A label with no option gets none
- **WHEN** `cap:workspaces` is declared and the field has no `workspaces` option
- **THEN** the apply creates no option, and the drift check reports the label as having no option

### Requirement: The drift check reports an option whose description differs from its label's
The out-of-band drift check SHALL report each option of the troupe roadmap board's `Capability` field whose
description differs from its `cap:<option>` label's declared description, naming the option and saying that the next
approved apply sets it.

#### Scenario: A stale description
- **WHEN** `cap:runs`'s declared description has changed and the `runs` option still has the old one
- **THEN** the drift check prints a difference naming `runs` and the board, and exits 1

#### Scenario: Matching descriptions
- **WHEN** every option with a label has its label's description
- **THEN** the drift check reports no description difference for the board's capabilities
