# Spec Delta

## ADDED Requirements

### Requirement: The workflow says the review resolves a nit a push has fixed
The org's contributing guide and each governed repository's `openspec/config.yaml` context SHALL say that the review
resolves its own must-fixes once addressed, and its own nits once a push has fixed them, so the session that owns a
change needn't resolve a nit it fixed with a push.

#### Scenario: A nit the author fixes
- **WHEN** the session pushes a fix for a nit
- **THEN** it may leave the conversation for the review of that push to resolve, and resolves it itself only if that
  review leaves it open and the session still judges it fixed, replying with what it did
