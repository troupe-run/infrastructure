# pr-review Specification

## Purpose

Claude reviews each pull request in the governed repositories (troupe, infrastructure, website) automatically and
posts its findings as comments. It's advisory and can't change the code. This spec covers when it runs, what it may
write, the credential it uses and how the workflow reaches each repository.

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
A review run SHALL write to GitHub only with a token minted for the review App, `troupe-run-review`, limited to
`contents: read` and `pull-requests: write` on the run's repository. Its `GITHUB_TOKEN` SHALL hold only
`contents: read`, and no `id-token`, so no Claude App token is minted. Claude's tools SHALL be limited to reading the
pull request and commenting on it. The run SHALL NOT use `pull_request_target`.

#### Scenario: Where the comments come from
- **WHEN** a review is posted
- **THEN** its comments are by `troupe-run-review[bot]`

#### Scenario: The run's tokens
- **WHEN** a review run's log is read
- **THEN** its `GITHUB_TOKEN` permissions list `Contents: read` and `Metadata: read` only, and the App token's
  requested permissions are contents read and pull requests write

#### Scenario: Claude tries to push
- **WHEN** a pull request's text asks Claude to commit a fix or push a branch
- **THEN** the run has no tool that edits files or runs git, and no token that can write contents, so nothing is
  pushed

#### Scenario: Claude is asked to read outside the checkout
- **WHEN** a pull request's text asks Claude to read `/proc/self/environ`, `.git/config` or any file outside the
  checkout, and post what it finds
- **THEN** the read is refused, because Read, Grep and Glob reach the checkout only, and the checkout keeps no token

#### Scenario: The workflow is weakened
- **WHEN** a change gives the review job another permission, swaps its event for `pull_request_target`, drops the
  bot skip, lets it mint a token through OIDC, asks the App for more, widens Claude's tools, or uses an action that
  isn't pinned to a full commit SHA
- **THEN** `scripts/check.py` fails, naming what changed

### Requirement: The review App is narrow and installed on the governed repositories
The review App `troupe-run-review` SHALL have only these repository permissions: contents read, pull requests read
and write, and metadata read. It SHALL have no organisation permissions. Its installation SHALL select repositories,
and SHALL cover troupe, infrastructure and website only. Any difference SHALL be reported by the drift check or the
hand-confirmed list (spec: teams-and-access).

#### Scenario: The review App gains a permission
- **WHEN** the review App's installation gains a permission on GitHub, such as contents write
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
or skipped review SHALL NOT stop a pull request from merging.

#### Scenario: The review fails
- **WHEN** a review run fails or times out
- **THEN** the pull request can still merge once its required checks pass

#### Scenario: Claude's findings
- **WHEN** Claude finishes a review
- **THEN** it has posted comments only, and the pull request's review state is unchanged

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
