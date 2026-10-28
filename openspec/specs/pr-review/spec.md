# pr-review Specification

## Purpose

Claude reviews each pull request in the governed repositories (troupe, infrastructure, website) automatically and
posts each finding as a conversation, labelled must-fix, nit or decision for who resolves it. It can't change the code
or approve; an unresolved conversation blocks the merge through the ruleset. This spec covers when it runs, what it may
write, how its findings are tiered and resolved, the credentials it uses and how the workflow reaches each repository.

## Requirements

### Requirement: Claude reviews each pull request when it's opened and updated
A pull request in troupe, infrastructure or website SHALL get a review from Claude when it's opened, reopened, marked
ready for review, or pushed to. Drafts SHALL be reviewed too. The review SHALL be posted as comments on the pull
request: inline on the lines it concerns, and one top-level summary.

#### Scenario: A pull request is opened
- **WHEN** a member opens a pull request from a branch of troupe, infrastructure or website
- **THEN** a review run starts, and Claude's comments appear on the pull request once it finishes

#### Scenario: A pull request is updated
- **WHEN** a member pushes a new commit to a pull request's branch
- **THEN** a new review run starts for the new head, and a run still going for the earlier head is cancelled

#### Scenario: A draft
- **WHEN** a member opens a draft pull request
- **THEN** it's reviewed as any other pull request is

### Requirement: Pull requests opened by a bot, or from a fork, aren't reviewed
A pull request whose author is a bot SHALL NOT start a review. That covers Dependabot, release-please's release pull
requests through `troupe-run-release`, and any App's. A pull request from a fork SHALL NOT get the review's credential,
so it SHALL NOT be reviewed automatically.

#### Scenario: A release pull request
- **WHEN** `troupe-run-release[bot]` opens or updates troupe's release pull request
- **THEN** the review job is skipped, and the run doesn't fail

#### Scenario: A Dependabot pull request
- **WHEN** Dependabot opens a pull request
- **THEN** the review job is skipped, and the run doesn't fail

#### Scenario: A fork's pull request
- **WHEN** an outside contributor opens a pull request from a fork
- **THEN** the review job is skipped, the run doesn't fail, and the credential isn't exposed to it

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

### Requirement: The review App is narrow and installed on the governed repositories
The review App `troupe-run-review` SHALL have only these repository permissions: contents read and write, which
resolving a conversation needs (owner, 2026-10-28), pull requests read and write, and metadata read. It SHALL have no organisation permissions. Its installation SHALL select repositories,
and SHALL cover troupe, infrastructure and website only. Any difference SHALL be reported by the drift check or the
hand-confirmed list (spec: teams-and-access).

#### Scenario: The review App gains a permission
- **WHEN** the review App's installation gains a permission on GitHub, such as administration or workflows
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The declared review App matches
- **WHEN** the review App has exactly the declared permissions and repository selection
- **THEN** the drift check reports no difference for it

### Requirement: The review loads no settings from the repository
A review run SHALL load Claude Code settings from the user scope only, never from the repository's `.claude/`
directory or a local settings file. So the guard's Claude Code hooks, which are written for an agent working in the
owner's terminal, SHALL NOT run in it, and SHALL NOT widen the tools the review allows (owner, 2026-10-26).

#### Scenario: The repository holds the guard's hooks
- **WHEN** a pull request is reviewed in a repository whose `.claude/settings.json` holds the guard's hooks
- **THEN** the review reads the diff and posts its comments, and none of the guard's hooks runs

#### Scenario: A hook would grant a write
- **WHEN** the review is asked to close or retitle the pull request
- **THEN** it can't: no repository setting grants `gh pr close` or `gh pr edit`, and its tool list doesn't allow them

#### Scenario: The settings are widened
- **WHEN** a change makes the review load project or local settings
- **THEN** `scripts/check.py` fails, naming the setting sources

### Requirement: The review's credentials are org secrets set by hand
The review SHALL authenticate to Claude with `CLAUDE_CODE_OAUTH_TOKEN`, and mint its GitHub token with
`REVIEW_APP_PRIVATE_KEY`. Each SHALL be an org Actions secret visible to troupe, infrastructure and website only, set
by the owner from 1Password with a documented command that prints nothing. OpenTofu SHALL NOT hold either, and
`oob/README.md` SHALL record how each is made, checked by name and rotated.

#### Scenario: Checking the secret
- **WHEN** the owner lists each org secret's repositories, by name, never by value
- **THEN** exactly troupe, infrastructure and website are listed

#### Scenario: A failed read sets nothing
- **WHEN** the 1Password read fails while the documented command runs
- **THEN** no secret is set or overwritten

#### Scenario: The token has expired
- **WHEN** a review run's Claude credential is refused
- **THEN** the run fails with the action's authentication error, and nothing else is affected, because the review
  isn't a required check

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

### Requirement: The review checks the org's own rules
The review's instructions SHALL be written in one place, the workflow's prompt. It SHALL check the pull request against
the repository's `CLAUDE.md` as on the base branch, the org's contributing guide, the OpenSpec change's tasks and specs
against the diff, the linked issue's "Done when", and Conventional Commits, as well as for correctness bugs.

#### Scenario: An unticked task's code is in the diff
- **WHEN** a pull request implements a task its change's `tasks.md` leaves unticked, or ticks one whose code isn't there
- **THEN** Claude's review points it out

#### Scenario: A pull request edits CLAUDE.md
- **WHEN** a pull request changes `CLAUDE.md`
- **THEN** the review is guided by the base branch's `CLAUDE.md`, not the pull request's

### Requirement: The review workflow is delivered from this repository
The review workflow's source SHALL be this repository's `.github/workflows/claude-review.yml`. It SHALL be delivered to
troupe and website with the guard's files, listed in each one's `.github/guard-delivery.json` and changed only at its
source (spec: guard-delivery). It SHALL NOT be delivered to `.github`.

#### Scenario: The delivered workflow
- **WHEN** troupe's or website's `.github/workflows/claude-review.yml` is read after an apply
- **THEN** it has the source's content, and the repository's delivered list names it

#### Scenario: An edit in a governed repository
- **WHEN** someone changes the review workflow in troupe directly
- **THEN** the guard refuses the commit as a delivered file, and if it reaches GitHub, the next plan restores it

#### Scenario: .github
- **WHEN** the managed state is read after an apply
- **THEN** `.github` holds no review workflow

### Requirement: A review run names each permission denial in its log
When Claude is refused a tool call, the review run SHALL name the call in its log as a warning: the tool and its
input, cut short. The run SHALL show nothing else from the session, which stays hidden. A run with no denial SHALL say
so. Reporting SHALL use no secret, and SHALL NOT fail the run or stop the review's comments from being posted.

#### Scenario: A call is refused
- **WHEN** Claude tries a tool its list doesn't allow, such as fetching a URL
- **THEN** the run shows a warning naming that tool and its input, and the review's comments are still posted

#### Scenario: Nothing is refused
- **WHEN** a review finishes without a denial
- **THEN** the run's log says no call was refused, and shows no warning for it

#### Scenario: A denied input holds a workflow command
- **WHEN** a denied call's input holds a newline or `::`, for example text a pull request asked Claude to run
- **THEN** it's printed inside the one warning, and no workflow command runs from it

#### Scenario: The session's output stays hidden
- **WHEN** a review run's log is read
- **THEN** it shows the denials and the action's own summary, but not the session's messages or tool results

#### Scenario: The report is widened or dropped
- **WHEN** a change adds a step that runs another command, changes the reporting step, or gives the action
  `show_full_output` or `display_report`
- **THEN** `scripts/check.py` fails, naming the step or input

### Requirement: The review reads the org's contributing guide from its checkout
A review run SHALL check out troupe-run/.github's `CONTRIBUTING.md` into a path inside its workspace, keeping no
credential, and the prompt SHALL name that path. The review SHALL read the guide with its Read tool and gain no tool
to fetch a URL. In infrastructure, which holds the guide's source, the prompt SHALL also name that source.

#### Scenario: The review checks the guide
- **WHEN** a pull request is reviewed in troupe, infrastructure or website
- **THEN** Claude reads the guide from the checkout, and no call to fetch it is refused

#### Scenario: A pull request changes the guide's source
- **WHEN** a pull request in infrastructure changes `org-profile/CONTRIBUTING.md`
- **THEN** the prompt tells Claude that file is the guide's source, and the copy from troupe-run/.github is the
  version on its main

#### Scenario: The guide's checkout keeps a credential or leaves the workspace
- **WHEN** a change lets the guide's checkout keep its token, moves it outside the workspace, checks out another
  repository, or adds a tool that fetches URLs
- **THEN** `scripts/check.py` fails, naming what changed

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
A conversation's tier SHALL be the latest label `troupe-run-review[bot]` gave in it; a later reply of the review's
with no label keeps it. Only the review SHALL change a tier, by replying in the conversation with a new label line and its reason; the author argues for a change by
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
fixed step, in a job of its own after the review, SHALL resolve them. Claude's tools SHALL NOT grow.

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
