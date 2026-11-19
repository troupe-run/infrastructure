# Spec Delta

## ADDED Requirements

### Requirement: Every managed repository has auto-merge's labels
`hold` and `auto-merged` SHALL be declared once with the workflow's labels, and SHALL be part of every managed
repository's label set, with the same colour and description in each.

#### Scenario: A plan adds them
- **WHEN** a plan runs for troupe, which has neither label on GitHub
- **THEN** the plan shows `hold` and `auto-merged` being created there, with the declared colour and description

#### Scenario: The same in each repository
- **WHEN** the plan's labels for troupe, infrastructure and website are compared
- **THEN** `hold` and `auto-merged` have the same colour and description in each
