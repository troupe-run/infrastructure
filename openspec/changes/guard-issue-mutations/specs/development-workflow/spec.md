## MODIFIED Requirements

### Requirement: Agents' gh commands are allow-listed
In a Claude Code session, a `gh` command SHALL be allowed only if it is on the allow-list:
- a read;
- an everyday workflow write: pull requests, issues, comments, sub-issues, project items, running workflows;
- a write to a throwaway repository in `troupe-run`.

Anything else SHALL be refused, including an unknown subcommand, an extension or an alias. The list SHALL be kept in
one place.

An everyday write SHALL be allowed only through its `gh` command, never as a GraphQL mutation, so that each write has
one way to do it. A refused GraphQL mutation SHALL be named in the refusal. When `gh` has its own command for that
mutation and the allow-list allows that command, the fix SHALL name it.

#### Scenario: A read
- **WHEN** an agent runs `gh run view`, `gh pr checks`, a `gh api` `GET`, or a GraphQL query with no mutation
- **THEN** the command is allowed

#### Scenario: A workflow write
- **WHEN** an agent runs `gh pr create`, `gh issue comment`, `gh pr merge` without `--admin`, or `gh project
  item-add`
- **THEN** the command is allowed

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

#### Scenario: An unknown subcommand
- **WHEN** an agent runs a `gh` subcommand the list doesn't name, or a `gh` extension
- **THEN** the command is refused, and the message says it isn't on the allow-list

#### Scenario: An alias
- **WHEN** an agent runs `gh alias set`, or a command through a `gh` alias
- **THEN** the command is refused

#### Scenario: An unlisted API write
- **WHEN** an agent sends a `gh api` write to an endpoint the list doesn't name
- **THEN** the command is refused

#### Scenario: A throwaway repository
- **WHEN** an agent creates `troupe-run/infra-probe-20261013`, `troupe-run/spike-x` or `troupe-run/bakeoff-x`, or
  writes anything to one, rulesets included
- **THEN** the command is allowed

#### Scenario: Deleting a probe repository
- **WHEN** an agent deletes `troupe-run/infra-probe-20261013`
- **THEN** the command is allowed

#### Scenario: Deleting or unarchiving a spike or bake-off record
- **WHEN** an agent deletes, archives or unarchives a `troupe-run/spike-*` or `troupe-run/bakeoff-*` repository
- **THEN** the command is refused, and the message says it is the owner's

#### Scenario: A mention isn't a command
- **WHEN** an agent's commit message, or a quoted word, mentions `gh pr merge --admin` or `gh auth token`
- **THEN** the command is allowed
