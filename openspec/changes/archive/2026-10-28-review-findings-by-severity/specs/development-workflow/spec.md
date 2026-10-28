## MODIFIED Requirements

### Requirement: Agents don't act as the owner
In a Claude Code session, a `gh` command that performs an act reserved for the owner SHALL be refused, in any
repository, with a fix naming the owner, or this repository for anything OpenTofu manages. The acts are:
- merging a pull request, by any route;
- approving or rejecting a deployment;
- changing a ruleset, branch protection or an environment;
- org and repository administration;
- reading or changing the login's credentials.

#### Scenario: An admin merge
- **WHEN** an agent runs `gh pr merge 17 --rebase --admin`
- **THEN** the command is refused, and the message says to ask the owner to merge it

#### Scenario: A plain merge
- **WHEN** an agent runs `gh pr merge 32 --rebase` or `gh pr merge 32 --auto`, in a repository outside the throwaway
  ones
- **THEN** the command is refused, and the message says the owner merges once every conversation is resolved: on a
  blocked pull request `gh pr merge` turns on auto-merge, which would land it later without the owner looking again

#### Scenario: A merge through the API
- **WHEN** an agent merges a pull request with `gh api` (REST `pulls/<n>/merge`, or GraphQL `mergePullRequest`,
  `enablePullRequestAutoMerge` or `enqueuePullRequest`)
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
- a request for a built-in command's help.

Anything else SHALL be refused, including an unknown subcommand, an extension or an alias. The list SHALL be kept in
one place.

#### Scenario: A read
- **WHEN** an agent runs `gh run view`, `gh pr checks`, a `gh api` `GET`, or a GraphQL query with no mutation
- **THEN** the command is allowed

#### Scenario: A workflow write
- **WHEN** an agent runs `gh pr create`, `gh issue comment`, `gh pr ready`, or `gh project item-add`
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
- **WHEN** an agent runs `gh`, one of `gh`'s own command groups, any words that aren't flags, and `--help` or `-h` as
  the last word, such as `gh pr --help`, `gh codespace -h`, `gh repo create myrepo --help` or `gh pr create --help`
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

### Requirement: The guard grants the gh commands it allows
In a Claude Code session, the guard SHALL grant a `gh` read or an everyday issue, pull request, comment or project-item
write that no rule refuses, so that it runs without a prompt or auto mode's check. Only a guard identical to the one on
`origin/main` SHALL grant. Anything else SHALL get no grant, and is refused or left to Claude Code as before. A
person's own `deny` and `ask` rules SHALL still apply to a granted command.

#### Scenario: A routine write is granted
- **WHEN** an agent runs `gh pr ready 74` or `gh issue edit 29 --type Feature`, with the guard matching `origin/main`
- **THEN** the command runs without a prompt, in auto mode as well

#### Scenario: A command the guard allows but doesn't grant
- **WHEN** an agent runs `gh pr checkout 32`, `gh workflow run tofu.yml`, `gh api repos/troupe-run/troupe`, or a
  write to `troupe-run/infra-probe-20261013`
- **THEN** the guard doesn't grant it, and Claude Code decides as it does today

#### Scenario: A guard edited on a branch
- **WHEN** the `scripts/guard.py` running differs from the one on `origin/main`, or `origin/main` can't be read
- **THEN** the guard grants nothing, and still refuses what its rules refuse

#### Scenario: The person's own rules
- **WHEN** a person's settings hold a `deny` or `ask` rule that matches a command the guard grants
- **THEN** that rule applies: the command is refused or prompts

## ADDED Requirements

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

#### Scenario: Reopening a conversation
- **WHEN** an agent sends `unresolveReviewThread`
- **THEN** the command is refused

### Requirement: Review findings are acted on before a change is archived
The org's contributing guide and each governed repository's `openspec/config.yaml` context SHALL say that, before the
change is archived, the session that owns it waits for the review of its last push and acts on each finding by its
tier: it fixes or answers each must-fix and nit, resolves only nits, and raises each decision, and each must-fix it
disputes, with the owner.

#### Scenario: A change's tasks
- **WHEN** a change is proposed in troupe, infrastructure or website
- **THEN** its tasks include acting on the review's findings before the archive

#### Scenario: A nit the author won't fix
- **WHEN** the session decides a nit isn't worth fixing
- **THEN** it replies saying why, or links the follow-up issue it raised, then resolves the conversation
