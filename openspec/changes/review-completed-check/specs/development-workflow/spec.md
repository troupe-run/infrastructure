# Spec Delta

## ADDED Requirements

### Requirement: The workflow docs say the review of the head must complete
`docs/development-workflow.md` SHALL say, next to "the review of the last push", that a pull request can't merge
until the review of its head has completed, which the required `claude review completed` check reports, and that a
review cancelled or failed with no run after it is re-run with `gh run rerun <id>`, the ID the check names. It SHALL
say a must-fix fixed by a push gets no reply, and a reply that needs a discussion is posted before any push.

#### Scenario: An agent's last review was cancelled
- **WHEN** an agent's pull request shows no open finding, but its `claude review completed` check has failed
- **THEN** the workflow docs tell it that the head isn't reviewed yet, and to re-run the run the check names before
  marking it ready

#### Scenario: An agent fixes a must-fix
- **WHEN** an agent pushes a fix for a must-fix, following the workflow docs
- **THEN** it posts no reply saying it's fixed, so no reply's review cancels the push's review; a reply that needs a
  discussion ("this isn't a bug, because…") is posted before the push

#### Scenario: The docs and the check agree
- **WHEN** this repository's tests run
- **THEN** they fail if `docs/development-workflow.md` doesn't name `claude review completed`
