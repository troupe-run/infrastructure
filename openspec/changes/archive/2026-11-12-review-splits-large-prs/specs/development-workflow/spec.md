## MODIFIED Requirements

### Requirement: The workflow docs say what a passing review means
`docs/development-workflow.md`, under "Claude's review", SHALL say that a passing `claude review completed` means the
head's review finished and its sessions read every changed source and test file in full, that a warning names unread
prose, that data is left to its tests, and that a pass doesn't mean the code has no bugs or the owner's review can be
skipped. It SHALL say which files are which kind, how a large pull request's reading is split, and what to do when the
check fails.

#### Scenario: An agent's check fails for coverage
- **WHEN** an agent's pull request shows no open finding, and `claude review completed` fails because changed source
  or test files weren't read in full, even after the follow-up session, or coverage couldn't be measured
- **THEN** the workflow docs tell it the pull request hasn't been reviewed, and not to mark it ready until a review
  reads the code (re-run the run) or the owner says otherwise

#### Scenario: An agent's check passes with a warning
- **WHEN** an agent's pull request shows no open finding, and `claude review completed` passes with a warning naming
  prose the review didn't read in full
- **THEN** the workflow docs tell it the check has passed and it may mark the pull request ready, and that the warning
  stays on the run for the owner to see

#### Scenario: An agent sees several review sessions
- **WHEN** an agent's pull request gets a review run with three part sessions and a follow-up session
- **THEN** the workflow docs tell it that's one review: one summary comment, findings from every session, and one check

#### Scenario: The docs and the check agree
- **WHEN** this repository's tests run
- **THEN** they fail if "Claude's review" in `docs/development-workflow.md` doesn't say what a passing review means
