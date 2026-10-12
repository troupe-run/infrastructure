# development-workflow Specification

## Purpose
The rules every governed repository enforces on its own development, for every contributor, human or agent: which
actions are refused, how a refusal reads, and how an owner-granted override is recorded. A governed repository is one
that receives the guard: this repository and `troupe`. These rules govern how the org builds software; they are not
features of any product.

## Requirements

### Requirement: Refusals name the rule and the fix
Every guardrail that blocks an action SHALL say which rule blocked it and what to do instead, and SHALL leave the
repository unchanged by the blocked action.

#### Scenario: A blocked action explains itself
- **WHEN** any guardrail refuses an action
- **THEN** the message names the rule and gives the fix
- **AND** the action has had no effect on the repository

### Requirement: No commits on main
A commit made while `main` is checked out SHALL be refused. Work happens on a branch and reaches `main` through a
pull request.

#### Scenario: Committing on main
- **WHEN** a contributor commits with `main` checked out
- **THEN** the commit is refused and the message says to create a branch

#### Scenario: Committing on a branch
- **WHEN** a contributor commits on any other branch, and the other commit rules are met
- **THEN** the commit is made

### Requirement: Commit messages are Conventional Commits
A commit message's first line SHALL be `type(scope): subject` or `type: subject`, with an optional `!` before the
colon to mark a breaking change. The type is one of `feat`, `fix`, `docs`, `build`, `ci`, `test`, `refactor`,
`perf`, `style`, `chore` or `revert`. Messages git writes itself for fixups and squashes are accepted.

#### Scenario: A conventional message
- **WHEN** a contributor commits with the message `feat(cli): add --version`
- **THEN** the commit is made

#### Scenario: A message without a type
- **WHEN** a contributor commits with the message `Add the version flag`
- **THEN** the commit is refused, and the message shows the expected form with an example

#### Scenario: An unknown type
- **WHEN** a contributor commits with the message `feature: add --version`
- **THEN** the commit is refused, and the message lists the accepted types

#### Scenario: Autosquash messages
- **WHEN** a contributor commits with `git commit --fixup` or `--squash`
- **THEN** the commit is made

### Requirement: Checks pass before a commit
A commit SHALL be refused unless the repository's full check (`scripts/check.py`) passes on the work being
committed.

#### Scenario: A failing check
- **WHEN** a contributor commits while a gate fails
- **THEN** the commit is refused and the message names the failing gate

#### Scenario: The check is never silent and never endless
- **WHEN** the check runs before a commit
- **THEN** it is announced before it starts, and its output appears as it runs
- **AND** if it is still running after a set timeout (default 10 minutes, defined in one place), it is stopped
  and the commit is refused with a message naming the timeout

### Requirement: Archived changes are complete
A commit that adds or changes an archived OpenSpec change SHALL be refused while that change's task list has an
unticked task.

#### Scenario: Archiving with an unticked task
- **WHEN** a commit adds a change under `openspec/changes/archive/` whose tasks include an unticked box
- **THEN** the commit is refused, and the message names the change and the unticked task

### Requirement: Commits need a matching OpenSpec change
A commit SHALL be refused unless the current branch has the same name as an OpenSpec change, active or archived on
that branch. This catches work however it was made, including files changed outside an editor.

#### Scenario: Committing on a branch with no matching change
- **WHEN** a contributor commits on branch `x` and no change named `x` exists, active or archived
- **THEN** the commit is refused, and the message says to propose the change or switch to its branch

#### Scenario: Committing on the change's branch
- **WHEN** a contributor commits on branch `x` and the change `x` exists, active or archived
- **THEN** the commit goes ahead (if the other commit rules are met)

### Requirement: Edits need a matching OpenSpec change
In a Claude Code session, an edit made with the editing tools to any file in the repository SHALL be refused unless
the current branch is not `main` and has the same name as an OpenSpec change, active or archived on that branch.
This gives early feedback; the commit rule above is the backstop.

#### Scenario: Editing on main
- **WHEN** an agent edits a repository file with `main` checked out
- **THEN** the edit is refused and the message says to create a branch named after the change

#### Scenario: Editing on a branch with no matching change
- **WHEN** an agent edits a repository file on branch `x` and no change named `x` exists
- **THEN** the edit is refused and the message says to propose the change or switch to its branch

#### Scenario: Editing on the change's branch
- **WHEN** an agent edits a repository file on branch `x` and the change `x` exists, active or archived
- **THEN** the edit is allowed

#### Scenario: Editing outside the repository
- **WHEN** an agent edits a file outside the repository
- **THEN** this rule does not apply

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

### Requirement: Git's checks cannot be skipped from a session
In a Claude Code session, a git command that would skip or disable the repository's git hooks SHALL be refused.
That covers `--no-verify`, `-n` on `git commit`, and changing or overriding `core.hooksPath`.

#### Scenario: Skipping the hooks
- **WHEN** an agent runs `git commit --no-verify`
- **THEN** the command is refused

#### Scenario: Pointing the hooks elsewhere
- **WHEN** an agent runs a git command that sets `core.hooksPath` to anything other than the repository's hooks
- **THEN** the command is refused

### Requirement: Overrides are granted by a person and recorded
A refused action SHALL be allowed only through an override that a person grants outside the agent's own tool calls.
The override names the rule and a reason, applies to one action, and is appended to a local override log. An agent
SHALL NOT be able to grant itself an override.

#### Scenario: An owner-granted override
- **WHEN** a person grants an override for a rule with a reason, and the matching action is then attempted
- **THEN** that one action is allowed, and the log records the time, rule, reason and who granted it

#### Scenario: An override is used once
- **WHEN** a second matching action follows an override that has already been used
- **THEN** it is refused as usual

#### Scenario: An agent tries to grant itself an override
- **WHEN** an agent tries to create an override, through a command or by editing the override's files
- **THEN** the attempt is refused

### Requirement: Sessions start with the guardrails active
At the start of a Claude Code session in a governed repository, the repository's git hooks SHALL be made active if
they are not, and the session SHALL be told the workflow it is working under.

#### Scenario: Git hooks not yet active
- **WHEN** a session starts in a clone where `core.hooksPath` doesn't point at the repository's hooks
- **THEN** it is set to the repository's hooks, and the session is told so

### Requirement: Git hooks are on by default
The repository's own tooling SHALL turn its git hooks on wherever it runs, so a contributor doesn't have to remember
to. Running the repository's check, or starting a Claude Code session, SHALL make the git hooks active if they
aren't, and say so.

#### Scenario: Running the check in a fresh clone
- **WHEN** a contributor runs the repository's check in a clone where the git hooks aren't active
- **THEN** the hooks are turned on, the check says so, and later commits go through them

### Requirement: Commit messages are checked before a push
A push SHALL be refused while any commit it would send, on any branch, has a message that isn't a Conventional
Commit. The refusal names each such commit.

#### Scenario: Pushing a non-conventional commit
- **WHEN** a contributor pushes a branch carrying a commit whose first line is `Add a thing`
- **THEN** the push is refused, naming that commit and the expected form

#### Scenario: Pushing conventional commits
- **WHEN** every commit being pushed is a Conventional Commit
- **THEN** the push goes ahead

### Requirement: The rules are re-checked on GitHub
For every push to any branch and for every pull request, a GitHub check SHALL re-apply the git-level rules to the
commits involved: every commit message is a Conventional Commit, the branch matches an OpenSpec change (for any
branch other than `main`), and no archived change has an unticked task. It applies the same rules as the git hooks,
so a commit that skipped the local hooks is still caught.

#### Scenario: A push that skipped the local hooks
- **WHEN** a branch is pushed carrying a commit with a non-conventional message that was made with `--no-verify`
- **THEN** the GitHub check for that push fails and names the commit

#### Scenario: A pull request from a branch with no matching change
- **WHEN** a pull request's branch has no matching OpenSpec change
- **THEN** the GitHub check fails and names the rule

### Requirement: Guardrails behave the same on every platform
Every rule in this capability SHALL behave the same on Linux, macOS and Windows.

#### Scenario: The guardrail tests on each platform
- **WHEN** the guardrail tests run on Linux, macOS and Windows
- **THEN** they pass on each

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

### Requirement: The workflow's templates are org defaults
The pull request template and the issue forms (Bug, Feature and Decision) SHALL have their source in this repository
and be published to `troupe-run/.github` as the org's defaults. They SHALL describe the workflow in the order this
spec gives it, and SHALL NOT name a particular repository's product, so they suit any repository in the org.

#### Scenario: A repository with no templates of its own
- **WHEN** someone opens a pull request, or a new issue, in a troupe-run repository with no `.github/ISSUE_TEMPLATE/`
  and no pull request template of its own
- **THEN** the pull request's description starts from the org's template, and the issue chooser offers the Bug,
  Feature and Decision forms

#### Scenario: The PR template gives the settled order
- **WHEN** someone reads the pull request template
- **THEN** it says to archive the change on the branch before merging, and after the merge to comment on the issue
  with the pull request and the archived change

#### Scenario: The forms set the issue's type
- **WHEN** someone files an issue with the Bug, Feature or Decision form
- **THEN** the issue gets the matching issue type, and a Decision issue also gets the `needs:owner` label

#### Scenario: A form names something that doesn't exist
- **WHEN** a form names an issue type the org doesn't declare, or a label that isn't declared for every managed
  repository
- **THEN** the repository's checks fail and name the form and the missing type or label

#### Scenario: Vulnerability reports go to the security policy
- **WHEN** someone opens the issue chooser in a repository using the org's forms
- **THEN** it offers a blank issue and a link to the security policy for reporting a vulnerability
