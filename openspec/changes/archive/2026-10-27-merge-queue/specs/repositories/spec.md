## ADDED Requirements

### Requirement: Auto-merge is on exactly where the merge queue is
A managed repository SHALL allow auto-merge when its merge queue is on, and SHALL NOT otherwise. With the queue on, a
merge from the command line (`gh pr merge`) then adds the pull request to the queue, so the owner's bypass, which
skips the queue, is never the only way to merge from a terminal.

#### Scenario: A repository with its queue on
- **WHEN** a repository whose merge queue is on has its settings read from GitHub
- **THEN** auto-merge is allowed, and the plan shows no difference

#### Scenario: Merging from the command line queues the pull request
- **WHEN** the owner runs `gh pr merge <n>` on a pull request in a repository whose queue is on
- **THEN** the pull request joins the merge queue, and lands only once the queue's checks pass

#### Scenario: A repository with its queue off
- **WHEN** a repository whose merge queue is off has its settings read from GitHub
- **THEN** auto-merge isn't allowed
