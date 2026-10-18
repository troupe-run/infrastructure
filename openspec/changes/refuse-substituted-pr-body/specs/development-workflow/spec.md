## MODIFIED Requirements

### Requirement: Pull requests close an issue
In a Claude Code session, opening a pull request into the repository the session works in SHALL be refused unless
its description closes an issue with a closing keyword (`Closes`, `Fixes` or `Resolves`, followed by an issue
reference). A pull request into a different repository is not checked. When the pull request's target repository
can't be determined, it SHALL be treated as the session's repository.

#### Scenario: A PR without a closing reference
- **WHEN** an agent opens a pull request into the session's repository whose description closes no issue
- **THEN** the request is refused and the message says to add `Closes #<issue>`

#### Scenario: A PR that closes an issue
- **WHEN** an agent opens a pull request whose description contains `Closes #22`
- **THEN** the request goes ahead

#### Scenario: A PR into another repository
- **WHEN** an agent opens a pull request into another repository, such as `troupe-run/.github`, whose description
  closes no issue
- **THEN** the request goes ahead

#### Scenario: A PR that names the session's repository explicitly
- **WHEN** an agent opens a pull request that names the session's repository as its target, in any form `gh`
  accepts, and its description closes no issue
- **THEN** the request is refused, as for any PR into the session's repository

#### Scenario: A PR whose target can't be determined
- **WHEN** an agent opens a pull request whose description closes no issue, and its target repository can't be
  worked out (an unrecognisable repository name, or this clone has no remote to compare with)
- **THEN** the request is refused, as for a PR into the session's repository

#### Scenario: A description built by the shell
- **WHEN** an agent opens a pull request into the session's repository whose `--body` is built by a shell expansion
  (command substitution with `$(...)` or backticks, including `$(cat <<'EOF' ... EOF)`, or a variable such as
  `$BODY` or `${BODY}`), and the text outside the expansion closes no issue
- **THEN** the request is refused, and the message says a description built by the shell can't be checked before
  it's sent, and to write it to a file and pass it with `--body-file`
- **AND** it does not say the description lacks a closing line

#### Scenario: An expanded description whose own text closes an issue
- **WHEN** an agent opens a pull request whose `--body` holds a shell expansion and, outside it, `Closes #22`
- **THEN** the request goes ahead, as it did before

#### Scenario: A description given with a short flag
- **WHEN** an agent opens a pull request whose description is given in any short-flag form `gh` accepts, such as
  `-b'Closes #22'`, `-b='Closes #22'`, `-Fpr.md`, or after grouped boolean flags (`-db 'Closes #22'`)
- **THEN** the check reads that description as `gh` does, and the request goes ahead when it closes an issue and is
  refused when it doesn't

#### Scenario: A flag's value that looks like a flag
- **WHEN** an agent opens a pull request where another flag's value is a word that looks like a flag, such as
  `--title --fill` or `--title -b`
- **THEN** the check reads that word as the value, as `gh` does, not as a flag

#### Scenario: Help for gh pr create
- **WHEN** an agent runs `gh pr create --help` or `gh pr create -h`
- **THEN** the request goes ahead, since it prints help and opens no pull request

### Requirement: Agents don't act as the owner
In a Claude Code session, a `gh` command that performs an act reserved for the owner SHALL be refused, in any
repository, with a fix naming the owner, or this repository for anything OpenTofu manages. The acts are:
- merging past a pull request's rules;
- approving or rejecting a deployment;
- changing a ruleset, branch protection or an environment;
- org and repository administration;
- reading or changing the login's credentials.

#### Scenario: An admin merge
- **WHEN** an agent runs `gh pr merge 17 --rebase --admin`
- **THEN** the command is refused, and the message says to ask the owner to merge it

#### Scenario: A merge through the API
- **WHEN** an agent merges a pull request with `gh api` (REST `pulls/<n>/merge`, or GraphQL `mergePullRequest`)
- **THEN** the command is refused

#### Scenario: Approving a deployment
- **WHEN** an agent posts to a workflow run's `pending_deployments`, or runs `approveDeployments` or
  `rejectDeployments`
- **THEN** the command is refused, and the message says the owner approves deployments

#### Scenario: Changing a ruleset or an environment
- **WHEN** an agent writes to a ruleset, a branch's protection or an environment, by REST or GraphQL
- **THEN** the command is refused, and the message points to this repository

#### Scenario: Repository and org administration
- **WHEN** an agent runs any of these:
  - `gh secret set`;
  - `gh repo edit`;
  - `gh label create`;
  - a `gh api` write to a repository's settings, Pages or the org's issue types
- **THEN** the command is refused, and the message points to this repository

#### Scenario: The token
- **WHEN** an agent runs `gh auth token`, or `gh auth status --show-token`
- **THEN** the command is refused

#### Scenario: Another organisation's repository
- **WHEN** an agent runs `gh pr merge --admin` on a repository outside `troupe-run`
- **THEN** the command is refused, as in `troupe-run`

#### Scenario: Help for an owner-only command
- **WHEN** an agent asks for the help of an owner-only command, such as `gh repo edit --help` or `gh label create -h`
- **THEN** the command goes ahead, as a help request (see "Agents' gh commands are allow-listed")

#### Scenario: The owner overrides it
- **WHEN** the owner grants an `owner-only` override in their own terminal, and the agent then runs the refused
  command
- **THEN** that one command is allowed and the override is logged

### Requirement: Agents' gh commands are allow-listed
In a Claude Code session, a `gh` command SHALL be allowed only if it is on the allow-list:
- a read;
- an everyday workflow write: pull requests, issues, comments, sub-issues, project items, running workflows;
- a write to a throwaway repository in `troupe-run`;
- a request for a built-in command's help: `gh`, a built-in command group, any words that aren't flags, and
  `--help` or `-h` as the last word.

Anything else SHALL be refused, including an unknown subcommand, an extension or an alias. The list SHALL be kept in
one place.

#### Scenario: A read
- **WHEN** an agent runs `gh run view`, `gh pr checks`, a `gh api` `GET`, or a GraphQL query with no mutation
- **THEN** the command is allowed

#### Scenario: A workflow write
- **WHEN** an agent runs `gh pr create`, `gh issue comment`, `gh pr merge` without `--admin`, or `gh project
  item-add`
- **THEN** the command is allowed

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

#### Scenario: Asking for help
- **WHEN** an agent runs `gh pr --help`, `gh codespace -h`, `gh repo create myrepo --help` or `gh pr create --help`
- **THEN** the command goes ahead, whatever the command it asks about would be refused for

#### Scenario: A help flag that is another flag's value
- **WHEN** an agent runs a command where `--help` or `-h` follows a flag, such as
  `gh label create x --description --help`, so `gh` reads it as that flag's value and runs the command
- **THEN** the command is judged as the command it runs, here refused as owner-only

#### Scenario: Help for an extension or an alias
- **WHEN** an agent runs `gh <extension> --help`, `gh extension exec <name> --help` or `gh <alias> --help`,
  including `gh`'s own alias `co`
- **THEN** the command is refused as before, because `gh` runs the extension or alias, and passes it `--help`,
  rather than printing help

### Requirement: A grant is only for a plain gh command
The guard SHALL grant only a Bash command that is exactly one `gh` command, with no substitution, variable,
redirection, glob, chaining or environment prefix, and whose every file read is inside the repository or the system
temp directory.

#### Scenario: A gh command combined with anything else
- **WHEN** an agent runs `gh pr ready 74 && rm -rf build`, `gh issue comment 1 --body "$(cat notes)"`, or
  `GH_TOKEN=x gh pr ready 74`
- **THEN** the guard doesn't grant it

#### Scenario: A body read from outside the repository
- **WHEN** an agent runs `gh issue comment 1 --body-file ~/.ssh/id_ed25519`
- **THEN** the guard doesn't grant it, so it can't skip auto mode's check for sending local data away

#### Scenario: Through PowerShell
- **WHEN** an agent runs `gh pr ready 74` through the PowerShell tool
- **THEN** the guard doesn't grant it

#### Scenario: An attachment from outside the repository
- **WHEN** an agent runs `gh issue comment 1 --body x --attach /etc/hosts`, or any granted command whose `--attach`
  could name a file outside the repository and the system temp directory, in any `<file>#<alt text>` reading `gh`
  might make of it
- **THEN** the guard doesn't grant it, as for `--body-file`

#### Scenario: An attachment from inside the repository
- **WHEN** an agent runs `gh pr comment 74 --body x --attach 'docs/shot.png#The new page'`
- **THEN** the guard may grant it, as for a `--body-file` inside the repository
