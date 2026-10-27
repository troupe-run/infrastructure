## ADDED Requirements

### Requirement: An agent resolves only a nit
The guard SHALL allow an agent the GraphQL mutation `resolveReviewThread`, which `gh` has no command for, only for a
conversation that `troupe-run-review[bot]` opened and whose tier, the label on the review's latest comment in it, is
nit. It SHALL read the conversation from GitHub before allowing it. Any other `resolveReviewThread`, and
`unresolveReviewThread`, SHALL be refused.

#### Scenario: A nit
- **WHEN** an agent resolves a conversation the review opened as a nit, or later re-labelled nit
- **THEN** the command is allowed

#### Scenario: A must-fix
- **WHEN** an agent resolves a conversation whose tier is must-fix, including a nit the review later re-labelled
  must-fix, or one where only the author's own reply says nit
- **THEN** the command is refused, and the fix says the review resolves it once it's addressed, and to raise a dispute
  with the owner

#### Scenario: A decision, an unlabelled finding, or a person's conversation
- **WHEN** an agent resolves a conversation labelled decision, one whose label doesn't parse, or one a person opened
- **THEN** the command is refused, and the fix says to ask the owner

#### Scenario: The conversation can't be read
- **WHEN** the guard can't read the conversation from GitHub, or the mutation names more than one conversation, or
  names one through a variable it can't read
- **THEN** the command is refused, saying why

#### Scenario: Reopening a conversation
- **WHEN** an agent sends `unresolveReviewThread`
- **THEN** the command is refused

### Requirement: Review findings are acted on before a change is archived
The org's contributing guide and each governed repository's `openspec/config.yaml` context SHALL say that, before the
change is archived, the session that owns it waits for the review of its last push and acts on each finding by its
tier: it fixes or answers each must-fix and nit, resolves only nits, and raises each decision, and each must-fix it
disputes, with the owner.

#### Scenario: A change's tasks
- **WHEN** a change is proposed in troupe, infrastructure or website
- **THEN** its tasks include acting on the review's findings before the archive

#### Scenario: A nit the author won't fix
- **WHEN** the session decides a nit isn't worth fixing
- **THEN** it replies saying why, or links the follow-up issue it raised, then resolves the conversation
