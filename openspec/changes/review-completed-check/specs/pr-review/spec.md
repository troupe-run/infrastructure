# Spec Delta

## MODIFIED Requirements

### Requirement: The review's credentials are org secrets set by hand
The review SHALL authenticate to Claude with `CLAUDE_CODE_OAUTH_TOKEN`, and mint its GitHub token with
`REVIEW_APP_PRIVATE_KEY`. Each SHALL be an org Actions secret visible to troupe, infrastructure and website only, set
by the owner from 1Password with a documented command that prints nothing. OpenTofu SHALL NOT hold either, and
`oob/README.md` SHALL record how each is made, checked by name and rotated.

#### Scenario: Checking the secret
- **WHEN** the owner lists each org secret's repositories, by name, never by value
- **THEN** exactly troupe, infrastructure and website are listed

#### Scenario: A failed read sets nothing
- **WHEN** the 1Password read fails while the documented command runs
- **THEN** no secret is set or overwritten

#### Scenario: The token has expired
- **WHEN** a review run's Claude credential is refused
- **THEN** the run fails with the action's authentication error, its `claude review completed` check fails, and the
  pull request can't merge until the token is renewed and the run re-run, or the owner bypasses the rules

### Requirement: The review is advisory
Claude SHALL NOT approve or request changes on a pull request, and the review job SHALL NOT be a required check. What
the review finds blocks a merge only through its open conversations (spec: rulesets), never through its review state.
That the review of the head completed SHALL be required, through the `claude review completed` check.

#### Scenario: The review fails
- **WHEN** a pull request's last review run fails or times out
- **THEN** the pull request can't merge until a review of its head completes, and then can once its other required
  checks pass and its open conversations are resolved

#### Scenario: Claude's findings
- **WHEN** Claude finishes a review
- **THEN** it has posted comments, and resolved only its own conversations, and the pull request's review state is
  unchanged

## ADDED Requirements

### Requirement: A check reports whether the review of a pull request's head completed
Each run of the review workflow SHALL report a check named `claude review completed` on the pull request's head. In a
run that reviews, it SHALL wait for the review and its resolving job, and pass only if both succeeded. If either, or
the gate before them, failed or was cancelled, it SHALL fail, and its message SHALL name the run to re-run with
`gh run rerun <id>`.

#### Scenario: The review completes
- **WHEN** a push starts a review, and the review and its resolving job succeed
- **THEN** `claude review completed` passes on that head

#### Scenario: The review is still running
- **WHEN** a review of the head is running
- **THEN** `claude review completed` hasn't passed yet, and the pull request can't merge

#### Scenario: The last review is cancelled
- **WHEN** the last run to review a head is cancelled, with no run after it
- **THEN** `claude review completed` fails on the head, naming the run to re-run, and the pull request can't merge

#### Scenario: The review fails
- **WHEN** the review job fails
- **THEN** `claude review completed` fails, and its message says `gh run rerun <id>` with that run's ID

#### Scenario: The gate can't read the conversations
- **WHEN** a reply's gate fails because it can't read the review conversations
- **THEN** `claude review completed` fails in that run, naming the run to re-run

### Requirement: The latest review of the head decides the check
When a commit has more than one `claude review completed` check, the one that counts SHALL be the latest. A
cancelled or failed review followed by one that completes SHALL pass, and a re-run that completes SHALL pass.

#### Scenario: A cancelled review, then a completed one
- **WHEN** a push's review is cancelled by a reply's review run on the same head, and the reply's run completes
- **THEN** the pull request's `claude review completed` passes

#### Scenario: A re-run completes
- **WHEN** a failed review run is re-run with `gh run rerun <id>` and its review completes
- **THEN** the pull request's `claude review completed` passes

### Requirement: A run that reviews nothing can't hide a review that didn't complete
In a run whose event needs no review (a bot's comment, a reply to a nit or a decision, a comment by someone without
write access, a comment that isn't a reply), `claude review completed` SHALL report the result of the latest run that
reviewed the pull request's head: pass if it completed, fail naming it if it didn't, and fail if no run has reviewed
the head or one is still running.

#### Scenario: The review's own comments after a cancelled review
- **WHEN** the last review of a head was cancelled, and a bot's comment then starts a run that reviews nothing
- **THEN** that run's `claude review completed` fails, naming the cancelled run to re-run

#### Scenario: A reply to a nit after a completed review
- **WHEN** the last review of a head completed, and a person replies to a nit
- **THEN** that run's `claude review completed` passes

#### Scenario: The run that reviewed the head can't be read
- **WHEN** a run that reviews nothing can't read the workflow's earlier runs
- **THEN** its `claude review completed` fails, saying the earlier review couldn't be read and how to re-run

### Requirement: A pull request that isn't reviewed by design isn't held by the check
`claude review completed` SHALL pass on a pull request that isn't reviewed by design: one opened by a bot, including
Dependabot's and release-please's, or from a fork. It SHALL be skipped on a merge group, which counts as passed, so the
merge queue isn't held up.

#### Scenario: A Dependabot pull request
- **WHEN** Dependabot opens a pull request
- **THEN** the review is skipped and `claude review completed` passes

#### Scenario: A release pull request
- **WHEN** `troupe-run-release[bot]` opens or updates troupe's release pull request
- **THEN** the review is skipped and `claude review completed` passes

#### Scenario: A fork's pull request
- **WHEN** an outside contributor opens a pull request from a fork
- **THEN** the review is skipped, no secret is used, and `claude review completed` passes

#### Scenario: The merge queue
- **WHEN** the merge queue builds a merge group
- **THEN** `claude review completed` reports as skipped on the group's commit, and the queue isn't held up waiting
  for it
