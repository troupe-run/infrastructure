# Spec Delta

## ADDED Requirements

### Requirement: Each repository receiving the review requires that it completed
troupe, infrastructure and website SHALL each require `claude review completed`, the review workflow's check that the
review of a pull request's head completed (spec: pr-review), and none of the review workflow's other jobs. It SHALL be
declared with the other required checks.

#### Scenario: A pull request whose last review didn't complete
- **WHEN** a pull request into troupe, infrastructure or website has passed every other required check, but the last
  review of its head was cancelled
- **THEN** GitHub refuses to merge it, naming `claude review completed`

#### Scenario: The declared names match the delivered review workflow
- **WHEN** this repository's tests run
- **THEN** they fail if a repository receiving `claude-review.yml` doesn't require `claude review completed`, or any
  repository requires another of its jobs
