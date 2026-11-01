# Spec Delta

## ADDED Requirements

### Requirement: The workflow docs say the review of the head must complete
`docs/development-workflow.md` SHALL say, next to "the review of the last push", that a pull request can't merge
until the review of its head has completed, which the required `claude review completed` check reports, and that a
review cancelled or failed with no run after it is re-run with `gh run rerun <id>`, the ID the check names.

#### Scenario: An agent's last review was cancelled
- **WHEN** an agent's pull request shows no open finding, but its `claude review completed` check has failed
- **THEN** the workflow docs tell it that the head isn't reviewed yet, and to re-run the run the check names before
  marking it ready

#### Scenario: The docs and the check agree
- **WHEN** this repository's tests run
- **THEN** they fail if `docs/development-workflow.md` doesn't name `claude review completed`
