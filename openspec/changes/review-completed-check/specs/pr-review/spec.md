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
Each run of the review workflow started by a pull request event SHALL report a check named `claude review completed`
on the pull request's head. It SHALL wait for the review and its resolving job, and pass only if both succeeded. If
either, or the gate before them, failed or was cancelled, it SHALL fail, and its message SHALL name the run to re-run
with `gh run rerun <id>`.

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

#### Scenario: The gate fails
- **WHEN** the gate job of a pull request event's run fails or is cancelled
- **THEN** `claude review completed` fails in that run, naming the run to re-run

### Requirement: The newest pull request event's run decides the check
The `claude review completed` that counts for a pull request SHALL be the one from the newest run started by a pull
request event on its head. A cancelled or failed review followed by such a run, or a re-run, that completes SHALL
pass.

#### Scenario: A re-run completes
- **WHEN** a cancelled review run is re-run with `gh run rerun <id>` and its review completes
- **THEN** the pull request's `claude review completed` passes, though the cancelled attempt's failure is still listed

#### Scenario: A newer run on the same head
- **WHEN** the pull request is reopened while its last review on the same head had failed, and the new run's review
  completes
- **THEN** the pull request's `claude review completed` passes

### Requirement: A comment's run doesn't change the check
A run started by a review comment SHALL NOT report `claude review completed`, and SHALL NOT change whether it passes:
the check stays as the newest pull request event's run left it. A reply's review that completes SHALL NOT pass a check
whose last pull request review was cancelled; that run is re-run instead.

#### Scenario: The review's own comments after a cancelled review
- **WHEN** the last review of a head was cancelled, and a bot's comment then starts a run that reviews nothing
- **THEN** `claude review completed` still fails, naming the cancelled run

#### Scenario: A reply cancels a push's review
- **WHEN** a reply to a must-fix starts a review that cancels the push's review still running, and the reply's
  review completes
- **THEN** `claude review completed` still fails, naming the push's run, and re-running that run, which judges the
  reply too, passes it

#### Scenario: A reply after a completed review
- **WHEN** the last review of a head completed, and a person then replies to a nit or a must-fix
- **THEN** `claude review completed` still passes

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
