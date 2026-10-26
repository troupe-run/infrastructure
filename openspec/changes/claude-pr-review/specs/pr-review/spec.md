# Spec Delta

## Purpose

Claude reviews each pull request in the governed repositories (troupe, infrastructure, website) automatically and
posts its findings as comments. It's advisory and can't change the code. This spec covers when it runs, what it may
write, the credential it uses and how the workflow reaches each repository.

## ADDED Requirements

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
A review run SHALL hold only `contents: read` and `pull-requests: write`, and no other token permission, `id-token`
included. Every write SHALL go through that run's `GITHUB_TOKEN`. No GitHub App token SHALL be minted. Claude's tools
SHALL be limited to reading the pull request and commenting on it. The run SHALL NOT use `pull_request_target`.

#### Scenario: The run's token
- **WHEN** a review run's log is read
- **THEN** its `GITHUB_TOKEN` permissions list `Contents: read`, `Metadata: read` and `PullRequests: write`, and
  nothing else

#### Scenario: Claude tries to push
- **WHEN** a pull request's text asks Claude to commit a fix or push a branch
- **THEN** the run has no tool that edits files or runs git, and no token that can write contents, so nothing is
  pushed

#### Scenario: The workflow is weakened
- **WHEN** a change gives the review job another permission, swaps its event for `pull_request_target`, drops the
  bot skip, lets it mint a token through OIDC, widens Claude's tools, or uses an action that isn't pinned to a full
  commit SHA
- **THEN** `scripts/check.py` fails, naming what changed

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

### Requirement: The review's credential is an org secret set by hand
The review SHALL authenticate to Claude with `CLAUDE_CODE_OAUTH_TOKEN`, an org Actions secret visible to troupe,
infrastructure and website only. The owner SHALL set it from 1Password with a documented command that prints nothing.
OpenTofu SHALL NOT hold it, and `oob/README.md` SHALL record how it's made, checked by name and rotated.

#### Scenario: Checking the secret
- **WHEN** the owner lists the org secret's repositories, by name, never by value
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
