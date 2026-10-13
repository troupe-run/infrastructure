## MODIFIED Requirements

### Requirement: The rules are re-checked on GitHub
For every push to any branch and for every pull request, a GitHub check SHALL re-apply the git-level rules to the
commits involved: every commit message is a Conventional Commit, the branch matches an OpenSpec change (for any
branch other than `main`, except a release branch that the release App alone has written), and no archived change has
an unticked task. It applies the same rules as the git hooks, so a commit that skipped the local hooks is still
caught.

#### Scenario: A push that skipped the local hooks
- **WHEN** a branch is pushed carrying a commit with a non-conventional message that was made with `--no-verify`
- **THEN** the GitHub check for that push fails and names the commit

#### Scenario: A pull request from a branch with no matching change
- **WHEN** a pull request's branch has no matching OpenSpec change
- **THEN** the GitHub check fails and names the rule

## ADDED Requirements

### Requirement: The release branch passes the branch rule, narrowly
The GitHub check SHALL exempt a branch from the branch-change rule only when its name starts with `release-please--`
and it adds at least one commit to `main`, every one authored by the release App's bot account. Every other rule,
the commit-message rule included, SHALL still apply to its commits. Until the bot account's address is recorded in
the guard, no branch SHALL be exempt.

#### Scenario: A release pull request
- **WHEN** a push or pull request is checked for `release-please--branches--main`, whose only commit, `chore: release
  main`, is authored by the release App's bot account
- **THEN** the GitHub check passes

#### Scenario: The release branch name on someone else's commits
- **WHEN** a branch named `release-please--branches--main` adds a commit authored by anyone other than the release
  App's bot account, alone or alongside the App's commits
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: The release App's commits on another branch
- **WHEN** a branch whose name doesn't start with `release-please--` and has no matching OpenSpec change carries only
  commits authored by the release App's bot account
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A release commit with a non-conventional message
- **WHEN** the release branch adds a commit authored by the release App's bot account whose message isn't a
  Conventional Commit
- **THEN** the GitHub check fails on the commit-message rule and names the commit

#### Scenario: A release branch that adds nothing
- **WHEN** a branch named `release-please--branches--main` adds no commit to `main`
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: Before the release App exists
- **WHEN** the guard doesn't yet record the release App's bot account, and a release branch is checked
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: The release branch after main moves on
- **WHEN** release-please rebuilds its branch on a newer `main` and force-pushes it
- **THEN** the push is judged by the commits the branch adds to `main`, not by the commits between the old and new
  heads, and passes

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
