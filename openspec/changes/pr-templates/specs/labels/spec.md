# Spec Delta

## ADDED Requirements

### Requirement: Every managed repository has the workflow's labels
The labels the workflow uses, such as `needs:owner`, which the Decision form applies, SHALL be declared once and
SHALL be part of every managed repository's label set, with the same colour and description in each.

#### Scenario: A repository without the label
- **WHEN** a plan runs for a managed repository that has no `needs:owner` label on GitHub
- **THEN** the plan shows `needs:owner` being created there, with the declared colour and description

#### Scenario: troupe's existing label is kept
- **WHEN** troupe's `needs:owner`, which it already had, is declared from the shared list and a plan runs
- **THEN** the plan shows no change to troupe's `needs:owner`
