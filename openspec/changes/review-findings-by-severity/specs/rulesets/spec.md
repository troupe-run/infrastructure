## ADDED Requirements

### Requirement: Pull requests merge only when every review conversation is resolved
On troupe, infrastructure and website, a pull request into `main` SHALL NOT be mergeable, or join the merge queue,
while any review conversation on it is unresolved, whoever opened it. The owner's pull-request bypass SHALL still
merge past it. The setting SHALL be declared once, in the repository module.

#### Scenario: An open finding
- **WHEN** a pull request's required checks have passed but a conversation the review opened is unresolved
- **THEN** GitHub refuses to merge it or add it to the merge queue

#### Scenario: Every conversation resolved
- **WHEN** every conversation on a pull request is resolved and its required checks have passed
- **THEN** it can be merged, through the queue where the repository has one

#### Scenario: The owner bypasses
- **WHEN** an org owner merges a pull request with an open conversation, choosing to bypass the rules
- **THEN** the merge succeeds

#### Scenario: The setting is turned off on GitHub
- **WHEN** someone turns off conversation resolution in a repository's `main` ruleset on GitHub
- **THEN** the next plan shows the difference, and an apply restores it
