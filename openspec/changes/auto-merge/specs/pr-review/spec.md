# Spec Delta

## ADDED Requirements

### Requirement: The review's result for the head is recorded for auto-merge
Each run that reports `claude review completed` SHALL record, as an artifact named `review-result`, the head SHA it
judged, its coverage (`complete`, `incomplete` or `unknown`) and its source-and-test floor. The record SHALL be written
whether the check passes or fails, and SHALL change nothing the check decides.

#### Scenario: A complete review
- **WHEN** a review of head A read every listed file
- **THEN** its run has a `review-result` artifact saying head A, coverage `complete`

#### Scenario: Prose left unread
- **WHEN** a review read every source and test file but left a Markdown file unread
- **THEN** the artifact says coverage `incomplete`, floor `all`, and `claude review completed` passes as before

#### Scenario: A bot's pull request
- **WHEN** the review is skipped for a Dependabot pull request
- **THEN** no `review-result` artifact says `complete` for its head
