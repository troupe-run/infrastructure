## ADDED Requirements

### Requirement: A folded capability label is replaced before it's removed
When no troupe spec names a declared `cap:*` label any more, because its spec now names other labels, every troupe
issue and pull request that carries it, open or closed, SHALL first get every label that spec now names, and then
lose the folded label. The label SHALL be removed from the declaration only once it's on nothing.

#### Scenario: A folded label whose spec names two labels
- **WHEN** troupe's `run-workspaces` spec names `cap:stages` and `cap:vcs`, and an issue carries
  `cap:run-workspaces` and `cap:stages`
- **THEN** the issue is given `cap:vcs`, then `cap:run-workspaces` is taken off it, and it keeps `cap:stages`

#### Scenario: Removing folded labels that are on nothing
- **WHEN** a pull request removes folded labels from troupe's declaration, and no troupe issue or pull request carries
  any of them
- **THEN** the plan deletes exactly those labels, changes no other label, and no issue or pull request loses a label

#### Scenario: A folded label still in use
- **WHEN** a pull request removes a folded label that a troupe issue still carries
- **THEN** its description lists that issue, and it isn't merged until the issue has been given the spec's labels and
  the folded label has been taken off it
