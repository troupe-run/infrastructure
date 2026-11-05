# Spec Delta

## ADDED Requirements

### Requirement: The workflow docs say what a passing review means
`docs/development-workflow.md`, under "Claude's review", SHALL say that a passing `claude review completed` means the
review of the head finished and its session read every changed file and diff the list names, and that it doesn't mean
the code has no bugs, that call sites were checked, or that the owner's review can be skipped. It SHALL say what the
list leaves out, and what to do when the check fails for coverage.

#### Scenario: An agent's check fails for coverage
- **WHEN** an agent's pull request shows no open finding, and `claude review completed` fails naming files not read
- **THEN** the workflow docs tell it the pull request hasn't been reviewed, and not to mark it ready until a review
  reads them or the owner says otherwise

#### Scenario: The docs and the check agree
- **WHEN** this repository's tests run
- **THEN** they fail if "Claude's review" in `docs/development-workflow.md` doesn't say what a passing review means
