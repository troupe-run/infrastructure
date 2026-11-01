# Spec Delta

## MODIFIED Requirements

### Requirement: Review findings are acted on before a change is archived
The org's contributing guide and each governed repository's `openspec/config.yaml` context SHALL say that, before the
change is archived, the session that owns it waits for the review of its last push and acts on each finding by its
tier: it fixes or answers each must-fix and nit, resolves only nits, and raises each decision, and each must-fix it
disputes, with the owner. They SHALL say the review resolves its own must-fixes once addressed, and a nit once a push
has fixed it, so the session needn't resolve a nit it fixed.

#### Scenario: A change's tasks
- **WHEN** a change is proposed in troupe, infrastructure or website
- **THEN** its tasks include acting on the review's findings before the archive

#### Scenario: A nit the author won't fix
- **WHEN** the session decides a nit isn't worth fixing
- **THEN** it replies saying why, or links the follow-up issue it raised, then resolves the conversation

#### Scenario: A nit the author fixes
- **WHEN** the session pushes a fix for a nit
- **THEN** it may leave the conversation for the review of that push to resolve, and resolves it itself only if that
  review leaves it open and the session still judges it fixed, replying with what it did
