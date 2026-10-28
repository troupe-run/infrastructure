# Spec Delta

## ADDED Requirements

### Requirement: The review judges a reply in a review conversation when it's posted
When a person with write access to the repository replies in one of a pull request's review conversations, a review
run SHALL start for the pull request, with no push and nothing re-run by hand. It SHALL be the same review a push
starts, of the pull request's current head, so it judges the reply with the rest of the conversations. Re-running a
review run by hand SHALL still work.

#### Scenario: The author answers a must-fix
- **WHEN** the author replies to an open must-fix with why the code is right
- **THEN** a review run starts, and either resolves the conversation, re-tiers it, or leaves it open, and its summary
  says which

#### Scenario: A burst of replies
- **WHEN** the author replies in three conversations within a minute
- **THEN** each reply cancels the run the one before it started, and the last reply's run judges all three

#### Scenario: A reply while a review is running
- **WHEN** a person replies in a conversation while a review of the pull request is running
- **THEN** that review is cancelled, and the reply's run reviews the pull request as a push's run would

#### Scenario: A push after a reply
- **WHEN** the author pushes while a reply's review is running
- **THEN** the reply's run is cancelled, and the push's run reviews the new head and judges the reply

#### Scenario: A reply's run failed
- **WHEN** a reply's review run fails
- **THEN** re-running it, or the pull request's last `claude review` run, judges the reply

### Requirement: Only a person's reply starts a review
A review comment SHALL start a review only when it replies to another comment in a conversation, its author is not a
bot and has write access to the repository, and the pull request isn't from a fork or opened by a bot. Any other review
comment SHALL start no review, SHALL NOT fail its run, and SHALL get no secret when it comes from a fork.

#### Scenario: The review's own comments
- **WHEN** `troupe-run-review[bot]` posts a finding, or a reply that re-tiers one
- **THEN** no review starts, and the run it causes is skipped

#### Scenario: A comment that opens a conversation
- **WHEN** a person posts a new review comment that doesn't reply to another
- **THEN** no review starts until the next push or reply

#### Scenario: An outside user replies
- **WHEN** someone without write access to the repository replies in a review conversation
- **THEN** no review starts, and the run it causes is skipped, not failed

#### Scenario: A reply on a fork's pull request
- **WHEN** someone replies in a review conversation on a pull request from a fork
- **THEN** no review starts, and the run gets no secret

#### Scenario: A reply on a bot's pull request
- **WHEN** a person replies in a conversation on a Dependabot or release pull request
- **THEN** no review starts

### Requirement: A skipped run doesn't cancel a running review
A run whose review job is skipped SHALL NOT cancel, or delay, a review run for the same pull request. Only a run whose
review job starts SHALL replace one that's running.

#### Scenario: The review posts its findings
- **WHEN** a running review posts five inline findings, each of which starts a run that's skipped
- **THEN** the review runs to its end, posts its summary, and its resolving job runs

#### Scenario: An outside user comments during a review
- **WHEN** someone without write access replies in a conversation while a review is running
- **THEN** the running review isn't cancelled

## MODIFIED Requirements

### Requirement: A review run can't change the repository
A review run SHALL write only with review App tokens for its repository: contents read and pull requests write in
Claude's job; contents write and pull requests write, which resolving needs, in the resolving job, where Claude doesn't
run and nothing is checked out. Each `GITHUB_TOKEN` SHALL hold only `contents: read`, and no `id-token`. Claude's tools
SHALL be limited to reading the pull request and commenting. The run SHALL NOT use `pull_request_target`.

#### Scenario: Where the comments come from
- **WHEN** a review is posted
- **THEN** its comments are by `troupe-run-review[bot]`

#### Scenario: The run's tokens
- **WHEN** a review run's log is read
- **THEN** each job's `GITHUB_TOKEN` permissions list `Contents: read` and `Metadata: read` only; the review job's App
  token asks for contents read and pull requests write, and the resolving job's for contents write and pull requests
  write

#### Scenario: Claude tries to push
- **WHEN** a pull request's text asks Claude to commit a fix or push a branch
- **THEN** Claude has no tool that edits files or runs git, and the job it runs in has no token that can write
  contents, so nothing is pushed

#### Scenario: Claude is asked to read outside the checkout
- **WHEN** a pull request's text asks Claude to read `/proc/self/environ`, `.git/config` or any file outside the
  checkout, and post what it finds
- **THEN** the read is refused, because Read, Grep and Glob reach the checkout only, and the checkout keeps no token

#### Scenario: The workflow is weakened
- **WHEN** a change gives either job another permission, runs Claude or a checkout in the resolving job, swaps its event for `pull_request_target`, drops the
  bot skip, lets it mint a token through OIDC, asks the App for more, widens Claude's tools, or uses an action that
  isn't pinned to a full commit SHA
- **THEN** `scripts/check.py` fails, naming what changed

#### Scenario: The reply trigger is widened
- **WHEN** a change starts the review on another event, such as `issue_comment` or `pull_request_review`, or on another
  review comment action, drops the reply-only, bot, write-access or fork skip, or moves the concurrency group back to
  the workflow, where a skipped run joins it
- **THEN** `scripts/check.py` fails, naming what changed
