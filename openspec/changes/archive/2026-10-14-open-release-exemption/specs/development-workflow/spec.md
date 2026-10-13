## MODIFIED Requirements

### Requirement: The release branch passes the branch rule, narrowly
The GitHub check SHALL exempt a branch from the branch-change rule only when it's named `release-please--*`, adds at
least one commit to `main`, all by the release App's bot, and lives in a repository (a pull request's head repository)
whose ruleset lets only the release App write those branches. Other rules SHALL still apply. With no repository named,
or no bot address in the guard, no branch SHALL be exempt.

#### Scenario: A release pull request
- **WHEN** a push or pull request in `troupe-run/troupe` is checked for `release-please--branches--main`, whose only
  commit, `chore: release main`, is authored by the release App's bot account
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
- **WHEN** the guard doesn't record the release App's bot account, and a release branch is checked
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A release branch in a repository without the release ruleset
- **WHEN** a push to `troupe-run/infrastructure` is checked for `release-please--branches--main`, whose only commit is
  authored by the release App's bot account
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A release branch from a fork
- **WHEN** a pull request into `troupe-run/troupe` comes from a fork's `release-please--branches--main`, whose only
  commit is authored by the release App's bot account
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A pull request whose head repository can't be read
- **WHEN** a pull request's event payload holds a head repository that isn't an object with a name
- **THEN** the GitHub check fails, saying it couldn't read the pull request's head repository and to re-run it

#### Scenario: A check that can't name its repository
- **WHEN** the check is run without a repository, and a release branch whose only commit is the release App's bot's is
  checked
- **THEN** the check fails on the branch-change rule

#### Scenario: The release branch after main moves on
- **WHEN** release-please rebuilds its branch on a newer `main` and force-pushes it
- **THEN** the push is judged by the commits the branch adds to `main`, not by the commits between the old and new
  heads, and passes
