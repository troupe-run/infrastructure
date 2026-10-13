## ADDED Requirements

### Requirement: Each everyday gh write has one way to do it
An everyday write SHALL be allowed only through its `gh` command, never as a GraphQL mutation, so that each write has
one way to do it. A refused GraphQL mutation SHALL be named in the refusal. When `gh` has its own command for that
mutation and the allow-list allows that command, the fix SHALL name it.

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
- **THEN** the command is refused, the message names `addLabelsToLabelable`, and the fix names
  `gh issue edit <n> --add-label <name>`

#### Scenario: A refused mutation with no allowed gh command
- **WHEN** an agent sends a GraphQL mutation the list doesn't name, and `gh` has no command for it or only an
  owner-only one (`deleteIssue` and `gh issue delete`)
- **THEN** the command is refused, the message names the mutation, and the fix doesn't point to a `gh` command
