# Spec Delta

## ADDED Requirements

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

#### Scenario: The owner overrides it
- **WHEN** the owner grants an `owner-only` override in their own terminal, and the agent then runs the refused
  command
- **THEN** that one command is allowed and the override is logged

### Requirement: Agents' gh commands are allow-listed
In a Claude Code session, a `gh` command SHALL be allowed only if it is on the allow-list:
- a read;
- an everyday workflow write: pull requests, issues, comments, sub-issues, project items, running workflows;
- a write to a throwaway repository in `troupe-run`.

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
