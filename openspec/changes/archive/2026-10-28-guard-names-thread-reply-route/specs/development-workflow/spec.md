## MODIFIED Requirements

### Requirement: Each everyday gh write has one way to do it
An everyday write SHALL be allowed only through its one way, never also as a GraphQL mutation or another endpoint. Its
one way is its `gh` command, or, for a write `gh` has no command for, the one `gh api` call the allow-list allows. A
refused mutation SHALL be named in the refusal. When the refused mutation or endpoint does a write that has an allowed
way, the fix SHALL name that way and SHALL NOT suggest adding to the allow-list.

#### Scenario: An everyday write sent as a GraphQL mutation
- **WHEN** an agent sends a GraphQL mutation that sets an issue's type (`updateIssueIssueType`), adds a "blocked by"
  link (`addBlockedBy`), adds a sub-issue (`addSubIssue`), edits an issue (`updateIssue`) or comments (`addComment`)
- **THEN** the command is refused, and the fix names the `gh` command that does it, such as
  `gh issue edit <n> --type <name>` or `gh issue comment <n>`

#### Scenario: The same write through gh
- **WHEN** an agent runs `gh issue edit 29 --type Feature` or `gh issue edit 29 --add-blocked-by 63`
- **THEN** the command is allowed

#### Scenario: A refused mutation that gh has a command for
- **WHEN** an agent sends a GraphQL mutation the list doesn't name, such as `addLabelsToLabelable`, and `gh` has an
  allowed command that does the same, here `gh issue edit --add-label`
- **THEN** the command is refused, the message names `addLabelsToLabelable`, the fix names
  `gh issue edit <n> --add-label <name>`, and the fix doesn't suggest asking the owner or adding to the list

#### Scenario: A review reply sent as a GraphQL mutation
- **WHEN** an agent replies in a review conversation with `addPullRequestReviewThreadReply`
- **THEN** the command is refused, the message names `addPullRequestReviewThreadReply`, and the fix names
  `gh api -X POST repos/<owner>/<repo>/pulls/<n>/comments -F in_reply_to=<comment id> -f body=...`

#### Scenario: A review reply sent to the replies endpoint
- **WHEN** an agent sends `gh api -X POST repos/troupe-run/troupe/pulls/186/comments/3012345678/replies -f body=...`
- **THEN** the command is refused, and the fix names
  `gh api -X POST repos/troupe-run/troupe/pulls/186/comments -F in_reply_to=3012345678 -f body=...`

#### Scenario: Some refused mutations have a way and some don't
- **WHEN** an agent sends one GraphQL document with `addComment` and `deleteIssue`
- **THEN** the command is refused, the message names both, and the fix names `gh issue comment <n>` for `addComment`
  and says to ask the owner for the other

#### Scenario: A refused mutation with no allowed gh command
- **WHEN** an agent sends a GraphQL mutation the list doesn't name, and `gh` has no command for it or only an
  owner-only one (`deleteIssue` and `gh issue delete`)
- **THEN** the command is refused, the message names the mutation, and the fix doesn't point to a `gh` command

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

#### Scenario: The conversation's id is filled in by the shell
- **WHEN** an agent resolves a conversation whose id, in the query or in a `-f`/`-F` field, is a shell variable or
  substitution, such as `threadId: "$TID"` or `-f id="$TID"`
- **THEN** the command is refused without reading GitHub, and the fix says to write the conversation's id out in the
  command, not to check gh's login or network

#### Scenario: Reopening a conversation
- **WHEN** an agent sends `unresolveReviewThread`
- **THEN** the command is refused
