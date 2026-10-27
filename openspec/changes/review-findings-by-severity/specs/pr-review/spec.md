## MODIFIED Requirements

### Requirement: The review is advisory
The review SHALL NOT be a required check, and Claude SHALL NOT approve or request changes on a pull request. A failed
or skipped review SHALL NOT stop a pull request from merging. What blocks a merge is the review's open conversations,
through the ruleset (spec: rulesets), never the review's run or its review state.

#### Scenario: The review fails
- **WHEN** a review run fails or times out
- **THEN** the pull request can still merge once its required checks pass and its open conversations are resolved

#### Scenario: Claude's findings
- **WHEN** Claude finishes a review
- **THEN** it has posted comments, and resolved only its own conversations, and the pull request's review state is
  unchanged

## ADDED Requirements

### Requirement: Each finding is a must-fix, a nit or a decision
The review SHALL label each finding with one tier, named for who resolves it: must-fix (the review, once addressed),
nit (the author) or decision (the owner). The prompt SHALL define the tiers in one place, and SHALL say that a finding
the review is unsure between must-fix and nit is a must-fix. The summary comment SHALL list decisions and must-fixes
first.

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

### Requirement: A conversation's tier is the review's latest label in it
A conversation's tier SHALL be the label on the latest comment in it by `troupe-run-review[bot]`. Only the review SHALL
change a tier, by replying in the conversation with a new label line and its reason; the author argues for a change by
replying, and a label in anyone else's comment SHALL count for nothing.

#### Scenario: A must-fix turns out to be a choice
- **WHEN** the author replies to a must-fix that both ways are defensible, and the next review agrees
- **THEN** the review replies in the conversation labelled decision, saying why, and the conversation is the owner's

#### Scenario: A must-fix turns out to be small
- **WHEN** the author's reply shows a must-fix is only wording, and the next review agrees
- **THEN** the review replies labelled nit, and the author may resolve it

#### Scenario: The author relabels a finding
- **WHEN** the author replies to a must-fix with a comment whose first line is `**nit**`
- **THEN** the conversation is still a must-fix, the guard still refuses the author's resolve, and the next review
  decides

### Requirement: Every finding is a conversation on the pull request
The review SHALL post each finding as an inline comment, which opens a conversation, on the lines it's about. A
finding that isn't about particular lines SHALL go on the line closest to what it concerns, so that every finding,
whatever its tier, is a conversation that must be resolved before the merge.

#### Scenario: A finding about the change as a whole
- **WHEN** the review finds that a ticked task has nothing behind it in the diff
- **THEN** it posts the finding as a conversation on the task's line in `tasks.md`

#### Scenario: Nothing found
- **WHEN** the review finds nothing
- **THEN** it opens no conversation, and its summary says so

### Requirement: The review reads its earlier conversations on each run
Before Claude starts, a review run SHALL write the pull request's review conversations to a file in the workspace:
each one's state, its comments and their authors. Claude SHALL read it, SHALL NOT post again a finding an open
conversation already holds, and SHALL say in its summary what became of each earlier finding.

#### Scenario: A finding that's still there
- **WHEN** the review runs again after a push that didn't address an open finding
- **THEN** it doesn't post that finding a second time, and its summary lists it as still open

#### Scenario: A nit resolved without a fix
- **WHEN** the author resolved a nit, and the review now sees it's a real problem
- **THEN** it posts a new must-fix on the same lines, saying why

#### Scenario: The conversations can't be read
- **WHEN** reading the pull request's conversations fails
- **THEN** the run fails before Claude starts, saying so, and no conversation is resolved

### Requirement: The review resolves its own must-fix conversations once addressed
A review run SHALL resolve an open conversation only when Claude names it as addressed, because the problem is gone
from the diff or the author's reply settles it, and only when the review App opened it and its tier is must-fix. A
fixed workflow step SHALL resolve them with the review App's token. Claude's tools SHALL NOT grow.

#### Scenario: A must-fix is fixed
- **WHEN** the author pushes a fix for a must-fix and the next review no longer sees the problem
- **THEN** that run resolves the conversation, and the summary says it was fixed

#### Scenario: The author disagrees
- **WHEN** the author replies to a must-fix with a reason, and the next review still sees a problem
- **THEN** the conversation stays open, and the summary says it's disputed and needs the owner

#### Scenario: A decision
- **WHEN** a conversation is labelled decision
- **THEN** no review run resolves it, whatever the replies say

#### Scenario: Claude names a conversation it may not resolve
- **WHEN** Claude names a nit, a decision, a person's conversation, or one that doesn't exist on the pull request
- **THEN** the step resolves none of those, and names each one it skipped in the run's log

#### Scenario: The resolving step is widened
- **WHEN** a change lets the step resolve another author's conversation or another tier, gives Claude a tool that
  sends GraphQL, or asks the App for more than it holds
- **THEN** `scripts/check.py` fails, naming what changed
