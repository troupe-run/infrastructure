## MODIFIED Requirements

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

## ADDED Requirements

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

## REMOVED Requirements

### Requirement: The release branch passes the branch rule, narrowly
**Reason**: It also required every commit the branch adds to be authored by the release App's bot. A commit's author
is something the pusher writes, and the owner chose not to have GitHub-side checks infer identity from it (#47). The
ruleset already decides who can write the branch on troupe, so the author check added nothing there.
**Migration**: Replaced by "A release branch passes the branch rule where GitHub reserves its name". The repository
and fork limits carry over unchanged. A release branch on troupe passes the branch rule whoever authored its commits,
and one that adds no commit has nothing for the rule to refuse.
