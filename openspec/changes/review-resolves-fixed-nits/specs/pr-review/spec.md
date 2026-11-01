# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The review resolves its own must-fix conversations once addressed`
- TO: `### Requirement: The review resolves its own must-fixes once addressed, and its nits once fixed`

## MODIFIED Requirements

### Requirement: Each finding is a must-fix, a nit or a decision
The review SHALL label each finding with one tier, named for who resolves it: must-fix (the review, once addressed),
nit (the author, or the review once a push has fixed it) or decision (the owner). The prompt SHALL define the tiers in
one place, and SHALL say that a finding the review is unsure between must-fix and nit is a must-fix. The summary
comment SHALL list decisions and must-fixes first.

#### Scenario: A bug
- **WHEN** the review finds code that does the wrong thing, loses data, weakens a security fence, or a test whose name
  claims more than its body checks
- **THEN** its comment is labelled must-fix

#### Scenario: A stale path in a comment
- **WHEN** the review finds a comment that names a file the pull request moves
- **THEN** its comment is labelled nit

#### Scenario: A choice the design doesn't settle
- **WHEN** the review finds two defensible ways the pull request could go, the change's design doesn't choose, and the
  choice is hard to reverse or reaches beyond the pull request
- **THEN** its comment is labelled decision

#### Scenario: A cheap, local choice
- **WHEN** the review finds two defensible ways to write something that only this pull request's code depends on
- **THEN** its comment is labelled nit, and the author chooses

### Requirement: The review resolves its own must-fixes once addressed, and its nits once fixed
A review run SHALL resolve an open conversation only when Claude names it, and only when the review App opened it and
its tier is must-fix or nit. Claude SHALL name a must-fix whose problem is gone from the diff or whose author's reply
settles it, and a nit only when its problem is gone from the diff. A fixed step, in a job of its own after the review,
SHALL resolve them. Claude's tools SHALL NOT grow.

#### Scenario: A must-fix is fixed
- **WHEN** the author pushes a fix for a must-fix and the next review no longer sees the problem
- **THEN** that run resolves the conversation, and the summary says it was fixed

#### Scenario: A nit is fixed
- **WHEN** the author pushes a fix for a nit the review opened, leaves the conversation open, and the review of that
  push no longer sees the problem
- **THEN** that run resolves the conversation, and the summary says it was fixed

#### Scenario: A nit answered without a fix
- **WHEN** the author replies to a nit that it isn't worth fixing, and pushes nothing that fixes it
- **THEN** no review run resolves it, and the conversation stays open for the author to resolve

#### Scenario: The author resolves a nit first
- **WHEN** the author resolves a nit before the next review runs
- **THEN** the review leaves it resolved, and the summary says the author resolved it

#### Scenario: The author disagrees
- **WHEN** the author replies to a must-fix with a reason, and the next review still sees a problem
- **THEN** the conversation stays open, and the summary says it's disputed and needs the owner

#### Scenario: A decision
- **WHEN** a conversation is labelled decision
- **THEN** no review run resolves it, whatever the replies say or the diff shows

#### Scenario: Claude names a conversation it may not resolve
- **WHEN** Claude names a decision, an unlabelled conversation, a person's conversation, or one that doesn't exist on
  the pull request
- **THEN** the step resolves none of those, and names each one it skipped in the run's log

#### Scenario: The resolving step is widened
- **WHEN** a change lets the step resolve another author's conversation, a decision or an unlabelled conversation,
  gives Claude a tool that sends GraphQL, or asks the App for more than it holds
- **THEN** `scripts/check.py` fails, naming what changed
