## MODIFIED Requirements

### Requirement: The workflow docs say what a passing review means
`docs/development-workflow.md`, under "Claude's review", SHALL say that until #280 a passing `claude review completed`
means the review of the head finished and read at least one changed source or test file in full (or none changed),
that a warning names the files it didn't read, and that a pass doesn't mean the code has no bugs, call sites were
checked, or the owner's review can be skipped. It SHALL say which files count, and what to do when the check fails.

#### Scenario: An agent's check fails for coverage
- **WHEN** an agent's pull request shows no open finding, and `claude review completed` fails because the review read
  none of the changed source and test files, or coverage couldn't be measured
- **THEN** the workflow docs tell it the pull request hasn't been reviewed, and not to mark it ready until a review
  reads the code or the owner says otherwise

#### Scenario: An agent's check passes with a warning
- **WHEN** an agent's pull request shows no open finding, and `claude review completed` passes with a warning naming
  files the review didn't read in full
- **THEN** the workflow docs tell it the check has passed and it may mark the pull request ready, and that the warning
  stays on the run for the owner to see

#### Scenario: The docs and the check agree
- **WHEN** this repository's tests run
- **THEN** they fail if "Claude's review" in `docs/development-workflow.md` doesn't say what a passing review means
