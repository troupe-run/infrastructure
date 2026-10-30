## ADDED Requirements

### Requirement: A pull request opens as a draft and is marked ready once its review is clean
The org's contributing guide, `docs/development-workflow.md` and this repository's CLAUDE.md SHALL say that a pull
request is opened as a draft, the review's findings are acted on, and it's marked ready once the review of its last
push has nothing left to fix. It SHALL be a documented step, not a guard rule. The guard SHALL allow an agent to open
a draft (`gh pr create --draft`) and mark it ready (`gh pr ready <n>`).

#### Scenario: An agent opens its pull request
- **WHEN** an agent opens a pull request for its change, following the workflow docs
- **THEN** it opens it as a draft with `gh pr create --draft`, and the guard allows the command when its description
  closes an issue

#### Scenario: The review of the last push is clean
- **WHEN** the review of a draft's last push has left no must-fix or decision open
- **THEN** the agent marks it ready with `gh pr ready <n>`, and the guard allows the command

#### Scenario: Marked ready early
- **WHEN** a pull request is marked ready while the review still has findings open
- **THEN** no guard refuses it, and the `main` ruleset still refuses its merge while any conversation is unresolved
