# development-workflow Specification

## Purpose
The rules every governed repository enforces on its own development, for every contributor, human or agent: which
actions are refused, how a refusal reads, and how an owner-granted override is recorded. A governed repository is one
that receives the guard: this repository, `troupe` and `website`. These rules govern how the org builds software; they
are not features of any product.

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
committed. The exception: when the repository declares which paths need no check and which need only named scopes of
it, and every staged path is declared, the commit needs only what those paths need. What runs is announced.

#### Scenario: A failing check
- **WHEN** a contributor commits while a gate fails
- **THEN** the commit is refused and the message names the failing gate

#### Scenario: The check is never silent and never endless
- **WHEN** the check, or a scope of it, runs before a commit
- **THEN** it is announced before it starts, and its output appears as it runs
- **AND** if it is still running after a set timeout (default 10 minutes, defined in one place), it is stopped
  and the commit is refused with a message naming the timeout

#### Scenario: Only skipped paths are staged
- **WHEN** the repository's `scripts/check-paths.toml` skips `openspec/**`, and a commit stages only files under
  `openspec/`, including a change moved into `openspec/changes/archive/`
- **THEN** no check runs, and the commit goes ahead if the other commit rules are met
- **AND** the guard says the check was skipped, naming the skipped paths and `scripts/check-paths.toml`

#### Scenario: Only one scope's paths are staged
- **WHEN** the declaration has a scope `docs` covering `docs/**` and skips `openspec/**`, and a commit stages files
  under `docs/`, with or without files under `openspec/`
- **THEN** `scripts/check.py --scope docs` runs instead of the full check, and the guard says so

#### Scenario: Paths in two scopes are staged
- **WHEN** the declaration has scopes `api` and `docs`, and a commit stages a path in each
- **THEN** `scripts/check.py --scope api --scope docs` runs, with the names sorted, instead of the full check

#### Scenario: A path in two overlapping scopes is staged
- **WHEN** the declaration has a scope `blah` covering `path1/**` and `another/**`, and a scope `blech` covering
  `path1/**`, and a commit stages `path1/blah.py`
- **THEN** `scripts/check.py --scope blah --scope blech` runs

#### Scenario: A failing scope
- **WHEN** a scope runs before a commit and one of its gates fails
- **THEN** the commit is refused and the message names the failing gate

#### Scenario: A path the declaration doesn't name is staged
- **WHEN** a commit stages any path that is in neither the skip list nor a scope
- **THEN** the full check runs, as for any commit

#### Scenario: A file moved out of a read path
- **WHEN** the declaration skips `openspec/**`, and a commit moves a file from outside `openspec/` into it
- **THEN** the full check runs, because the file's old path counts as staged too

#### Scenario: No declaration
- **WHEN** the repository has no `scripts/check-paths.toml` staged, and a commit stages only files under `openspec/`
- **THEN** the full check runs, as for any commit

#### Scenario: The declaration itself is staged
- **WHEN** a commit stages `scripts/check-paths.toml`, whatever it declares
- **THEN** the full check runs

#### Scenario: A malformed declaration
- **WHEN** the staged `scripts/check-paths.toml` can't be parsed, has an unknown version, table or key, lists an
  entry that is neither an exact path nor a directory written `dir/**`, has an entry in the skip list that overlaps
  an entry in a scope, or names a scope outside `[a-z][a-z0-9_]*` or with a reserved name (`none`, `full`)
- **THEN** the commit is refused under `commit-checks`, and the message names the file, what's wrong with it and how
  to fix it

#### Scenario: Unstaged changes still refuse a skippable commit
- **WHEN** tracked files have unstaged changes, and the commit stages only skipped paths
- **THEN** the commit is refused for the unstaged changes, as before

### Requirement: CI reads the same declaration
The guard SHALL offer CI the same decision as the commit hook, from the same declaration: given a list of changed
paths, it says whether nothing, which scopes, or the full check must run, and gives the arguments for
`scripts/check.py`. An empty list SHALL mean the full check, and a malformed declaration SHALL fail with the commit
hook's message.

#### Scenario: Only skipped paths changed
- **WHEN** CI asks with changed paths that are all skipped
- **THEN** the guard answers `none`

#### Scenario: Only scoped and skipped paths changed
- **WHEN** CI asks with changed paths in the scopes `docs` and `api`, and possibly skipped paths
- **THEN** the guard answers `api,docs`, and the arguments `--scope api --scope docs`

#### Scenario: Any other path changed
- **WHEN** CI asks with changed paths that include one the declaration doesn't name, or the repository has no
  declaration
- **THEN** the guard answers `full`, with no arguments

#### Scenario: No changed paths
- **WHEN** CI asks with an empty list of changed paths
- **THEN** the guard answers `full`

#### Scenario: A malformed declaration in CI
- **WHEN** CI asks while the repository's declaration is malformed
- **THEN** the guard fails, naming the file, what's wrong and the fix, and gives no answer

### Requirement: A scope narrows only the tests
Given one or more scopes, a repository's check SHALL run every gate it runs for the full check, and SHALL narrow only
its tests, to those tagged with any of the scopes. It SHALL refuse a scope its declaration doesn't list.

#### Scenario: A scoped check
- **WHEN** `scripts/check.py --scope docs` runs in a repository that declares the scope `docs`
- **THEN** every gate runs, and the tests that run are exactly those tagged `docs`

#### Scenario: Two scopes
- **WHEN** `scripts/check.py --scope api --scope docs` runs
- **THEN** the tests that run are those tagged `api` or `docs`

#### Scenario: An undeclared scope
- **WHEN** `scripts/check.py --scope nope` runs and the declaration lists no scope `nope`
- **THEN** the check fails before running any gate, naming the scope and `scripts/check-paths.toml`

#### Scenario: A scope no test is tagged with
- **WHEN** `scripts/check.py --scope docs` runs, every other gate passes, and no test is tagged `docs`
- **THEN** the check passes, and says that no test is tagged `docs`, so there was nothing to test

### Requirement: Test tags cover what each test reads
Whenever a repository's tests run, a test SHALL fail if it reads a file under a scope's paths without that scope's
tag, or reads a file under a skipped path. Only files inside the repository count. The message SHALL name the test,
the file, and the tag to add or the skip entry it contradicts.

#### Scenario: A test reads a scope's path without its tag
- **WHEN** the declaration has a scope `docs` covering `docs/**`, and a test without the `docs` tag reads
  `docs/runs.md`
- **THEN** that test fails, naming `docs/runs.md` and saying to tag it `docs`

#### Scenario: A test reads a path in two scopes
- **WHEN** scopes `blah` and `blech` both cover `path1/**`, and a test tagged only `blah` reads `path1/x.json`
- **THEN** that test fails, saying to tag it `blech` too

#### Scenario: A test reads a skipped path
- **WHEN** the declaration skips `openspec/**`, and any test reads a file under `openspec/` in the repository
- **THEN** that test fails, naming the file and the skip entry, since the skip would let a change to it go untested

#### Scenario: Tags that cover the reads
- **WHEN** every file a test reads in the repository is in no group, or in scopes the test is tagged with
- **THEN** the tag check doesn't fail it

#### Scenario: Files outside the repository
- **WHEN** a test reads files in a temporary directory that its own fixture created
- **THEN** those reads don't count

### Requirement: A scope can tag whole test directories
A scope in the declaration MAY list the test directories it runs, as a `tests` list of `dir/**` entries. Every test
whose file is under one of them SHALL count as tagged with that scope, for selecting a scope's tests and for the tag
check alike, as if the tag were written on the test. A malformed `tests` list SHALL be a malformed declaration.

#### Scenario: A scope's tests directories are selected
- **WHEN** scope `vcs_git` declares `tests = ["packages/vcs-git/tests/**", "packages/core/tests/**"]`, and
  `scripts/check.py --scope vcs_git` runs
- **THEN** the tests that run are exactly those under the two directories, plus any test tagged `vcs_git` in its
  source

#### Scenario: Tests run in parallel
- **WHEN** the same scoped run's tests are spread across several worker processes
- **THEN** the same tests run as in a run in one process

#### Scenario: A directory tag covers what its tests read
- **WHEN** scope `docs` covers `docs/**` and declares `tests = ["tests/docs/**"]`, and an untagged test under
  `tests/docs/` reads `docs/runs.md`
- **THEN** the tag check doesn't fail it

#### Scenario: Two scopes list the same directory
- **WHEN** scopes `blah` and `blech` both list `tests/shared/**`
- **THEN** each test under `tests/shared/` counts as tagged with both, and runs for either scope

#### Scenario: A malformed tests entry
- **WHEN** a scope's `tests` is not a list, is an empty list, or holds an entry that is not a directory written
  `dir/**` by the rules for `paths` entries, or the skip list has a `tests` key
- **THEN** the declaration is malformed, and the message names the file, the scope, the entry and how to fix it

#### Scenario: A declaration without tests keys
- **WHEN** no scope declares `tests`
- **THEN** a test counts as tagged with a scope only when its source says so, as before

### Requirement: A tests entry that matches no test fails the run
When a test run collects from a directory that contains a scope's `tests` entry, and no collected test is under that
entry, the run SHALL fail with a failure that names the scope, the entry and the fix. The scope's own run SHALL fail
too, so it can't pass by running nothing.

#### Scenario: A renamed test directory
- **WHEN** scope `vcs_git` lists `packages/vcs-git/tests/**`, that directory was renamed, and the full test run runs
- **THEN** the run fails, naming `vcs_git`, `packages/vcs-git/tests/**` and `scripts/check-paths.toml`, and saying
  to correct or remove the entry

#### Scenario: The broken scope's own run
- **WHEN** the same declaration is in place and `scripts/check.py --scope vcs_git` runs
- **THEN** the check fails for the same reason, rather than passing because nothing was selected

#### Scenario: Tests run in parallel
- **WHEN** the same run's tests are spread across several worker processes
- **THEN** it fails with the same message

#### Scenario: A narrower run
- **WHEN** a contributor runs only one test file or directory, and a scope's `tests` entry lies outside it
- **THEN** that entry isn't checked, and the run doesn't fail for it

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

### Requirement: A hook git would skip is reported
Wherever the git hooks are made active, starting a Claude Code session or running the repository's check, each hook
that git would skip because it isn't executable SHALL be named, saying that git skips it and where it is fixed. It
SHALL NOT refuse anything, and it SHALL NOT change the file's mode. Where git runs a hook whatever its mode, nothing
SHALL be reported.

#### Scenario: A session starts where a hook isn't executable
- **WHEN** a Claude Code session starts in a clone of `website` whose `.githooks/pre-push` isn't executable
- **THEN** the session is told that git skips `.githooks/pre-push` because it isn't executable, and that the fix is
  made in `troupe-run/infrastructure`, not in the clone

#### Scenario: The check runs where a hook isn't executable
- **WHEN** a contributor runs the repository's check in that clone
- **THEN** the check names each hook git skips, still runs its gates, and its result is decided by those gates alone

#### Scenario: Every hook is executable
- **WHEN** a session starts, or the check runs, in a clone whose hooks are all executable
- **THEN** nothing about hook modes is reported

#### Scenario: A platform where git ignores the mode
- **WHEN** the check runs on Windows
- **THEN** nothing about hook modes is reported

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
branch other than `main`, except a release branch in a repository that reserves its name for the release App), and no
archived change has an unticked task. It applies the same rules as the git hooks, so a commit that skipped the local
hooks is still caught.

#### Scenario: A push that skipped the local hooks
- **WHEN** a branch is pushed carrying a commit with a non-conventional message that was made with `--no-verify`
- **THEN** the GitHub check for that push fails and names the commit

#### Scenario: A pull request from a branch with no matching change
- **WHEN** a pull request's branch has no matching OpenSpec change
- **THEN** the GitHub check fails and names the rule

#### Scenario: A Dependabot pull request in a governed repository
- **WHEN** a pull request in `troupe-run/troupe`, `troupe-run/infrastructure` or `troupe-run/website` comes from a
  branch named `dependabot/<ecosystem>/<package>-<version>`, which has no matching OpenSpec change
- **THEN** the GitHub check fails on the branch-change rule: no exemption covers a Dependabot branch

### Requirement: Pull request titles are Conventional Commits
For a pull request, the GitHub check SHALL apply the commit-message rule to the pull request's title, and SHALL
re-run when the title changes. A failing title is refused under `commit-message`, naming the title, with a fix that
says to edit the title.

#### Scenario: A conventional title
- **WHEN** a pull request is titled `chore: release main` and its commits pass every rule
- **THEN** the GitHub check passes

#### Scenario: A non-conventional title
- **WHEN** a pull request is titled `Release main`
- **THEN** the GitHub check fails on the commit-message rule, names the title, and says to edit it

#### Scenario: Renaming a pull request
- **WHEN** a pull request's title is edited from `Release main` to `chore: release main`, with no new commit
- **THEN** the GitHub check runs again and passes

#### Scenario: A push isn't a pull request
- **WHEN** a branch is pushed and no pull request is involved
- **THEN** the GitHub check checks no title

### Requirement: Guardrails behave the same on every platform
Every rule in this capability SHALL behave the same on Linux, macOS and Windows, and on every Python version troupe
supports.

#### Scenario: The guardrail tests on each platform
- **WHEN** the guardrail tests run on Linux, macOS and Windows
- **THEN** they pass on each

#### Scenario: The guardrail tests on each supported Python version
- **WHEN** the guardrail tests run on each Python version troupe supports (3.12 to 3.15 today), on each of Linux,
  macOS and Windows
- **THEN** they pass on each, and a pull request here can't merge until every one of those runs has passed

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
- a request for a built-in command's help.

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

### Requirement: The guard grants the gh commands it allows
In a Claude Code session, the guard SHALL grant a `gh` read or an everyday issue, pull request, comment or project-item
write that no rule refuses, so that it runs without a prompt or auto mode's check. Only a guard identical to the one on
`origin/main` SHALL grant. Anything else SHALL get no grant, and is refused or left to Claude Code as before. A
person's own `deny` and `ask` rules SHALL still apply to a granted command.

#### Scenario: A routine write is granted
- **WHEN** an agent runs `gh pr ready 74` or `gh issue edit 29 --type Feature`, with the guard matching `origin/main`
- **THEN** the command runs without a prompt, in auto mode as well

#### Scenario: A command the guard allows but doesn't grant
- **WHEN** an agent runs `gh pr merge 32 --rebase`, `gh workflow run tofu.yml`, `gh api repos/troupe-run/troupe`, or a
  write to `troupe-run/infra-probe-20261013`
- **THEN** the guard doesn't grant it, and Claude Code decides as it does today

#### Scenario: A guard edited on a branch
- **WHEN** the `scripts/guard.py` running differs from the one on `origin/main`, or `origin/main` can't be read
- **THEN** the guard grants nothing, and still refuses what its rules refuse

#### Scenario: The person's own rules
- **WHEN** a person's settings hold a `deny` or `ask` rule that matches a command the guard grants
- **THEN** that rule applies: the command is refused or prompts

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
- **THEN** it offers a blank issue and exactly one entry for reporting a vulnerability: GitHub's own, shown because
  the org publishes a security policy

#### Scenario: The chooser config doesn't duplicate GitHub's security entry
- **WHEN** the org's chooser config adds a contact link to the security policy
- **THEN** the repository's checks fail and say GitHub already shows that entry

### Requirement: A release branch passes the branch rule where GitHub reserves its name
The GitHub check SHALL exempt a branch from the branch-change rule when its name starts with `release-please--` and
it lives in a repository (a pull request's head repository) whose ruleset lets only the release App create or update
those branches. Who authored its commits SHALL NOT matter. Elsewhere, or with no repository named, no branch SHALL be
exempt. Every other rule SHALL still apply.

#### Scenario: A release pull request
- **WHEN** a push or pull request in `troupe-run/troupe` is checked for `release-please--branches--main`, whose only
  commit is `chore: release main`
- **THEN** the GitHub check passes

#### Scenario: A release branch in troupe, whoever authored it
- **WHEN** `release-please--branches--main` in `troupe-run/troupe` adds a conventional commit authored by someone other
  than the release App's bot account
- **THEN** the GitHub check doesn't fail on the branch-change rule

#### Scenario: A release branch in a repository without the release ruleset
- **WHEN** a push to `troupe-run/infrastructure` is checked for `release-please--branches--main`
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A release branch from a fork
- **WHEN** a pull request into `troupe-run/troupe` comes from a fork's `release-please--branches--main`
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A check that can't name its repository
- **WHEN** the check is run without a repository, and `release-please--branches--main` is checked
- **THEN** the check fails on the branch-change rule

#### Scenario: A pull request whose head repository can't be read
- **WHEN** a pull request's event payload holds a head repository that isn't an object with a name
- **THEN** the GitHub check fails, saying it couldn't read the pull request's head repository and to re-run it

#### Scenario: The release App's commits on another branch
- **WHEN** a branch in `troupe-run/troupe` whose name doesn't start with `release-please--` and has no matching
  OpenSpec change carries only commits authored by the release App's bot account
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A release commit with a non-conventional message
- **WHEN** the release branch in `troupe-run/troupe` adds a commit whose message isn't a Conventional Commit
- **THEN** the GitHub check fails on the commit-message rule and names the commit

#### Scenario: A release branch that changes a delivered file
- **WHEN** the release branch in `troupe-run/troupe` adds a commit, not made by the infrastructure App, that changes a
  delivered file
- **THEN** the GitHub check fails on the delivered-file rule

#### Scenario: The release branch after main moves on
- **WHEN** release-please rebuilds its branch in `troupe-run/troupe` on a newer `main` and force-pushes it
- **THEN** the GitHub check passes
