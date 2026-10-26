## ADDED Requirements

### Requirement: Pull requests close an issue, checked on GitHub
For every pull request in a governed repository, the GitHub check SHALL refuse it under `pr-closes-issue` unless its
description closes an issue, read the same way as the local rule: `Closes`, `Fixes` or `Resolves` (or another form of
them), followed by an issue in this or another repository. The check SHALL re-run when the description is edited. A
release pull request whose branch passes the branch rule as a release branch SHALL be exempt.

#### Scenario: A pull request with no closing line
- **WHEN** a pull request in `troupe-run/website` is opened on GitHub with the description `Bumps the build.`
- **THEN** the GitHub check fails under `pr-closes-issue`, names the pull request, and says to edit its description
  to add a line like `Closes #<issue>`

#### Scenario: An empty description
- **WHEN** a pull request is opened with no description
- **THEN** the GitHub check fails under `pr-closes-issue`, as for a description with no closing line

#### Scenario: A pull request that closes an issue
- **WHEN** a pull request's description contains `Closes #22`, `fixes #22` or `Resolves:
  https://github.com/troupe-run/infrastructure/issues/22`
- **THEN** the GitHub check doesn't fail under `pr-closes-issue`

#### Scenario: A pull request that closes an issue in another repository
- **WHEN** a pull request in `troupe-run/website` has the description `Closes troupe-run/infrastructure#173`
- **THEN** the GitHub check doesn't fail under `pr-closes-issue`

#### Scenario: Editing the description
- **WHEN** a pull request's description is edited from `Bumps the build.` to `Bumps the build. Closes #22`, with no new
  commit
- **THEN** the GitHub check runs again and doesn't fail under `pr-closes-issue`

#### Scenario: The release pull request
- **WHEN** a pull request in `troupe-run/troupe` from `release-please--branches--main` has a description that closes
  no issue
- **THEN** the GitHub check doesn't fail under `pr-closes-issue`

#### Scenario: A release branch from a fork
- **WHEN** a pull request into `troupe-run/troupe` comes from a fork's `release-please--branches--main` with a
  description that closes no issue
- **THEN** the GitHub check fails under `pr-closes-issue`, as well as on the branch-change rule

#### Scenario: A release branch where its name isn't reserved
- **WHEN** a pull request in `troupe-run/infrastructure` from `release-please--branches--main` has a description that
  closes no issue
- **THEN** the GitHub check fails under `pr-closes-issue`

#### Scenario: A Dependabot pull request
- **WHEN** Dependabot opens a pull request in a governed repository whose description closes no issue
- **THEN** the GitHub check fails under `pr-closes-issue`: no exemption covers a Dependabot pull request

#### Scenario: A push isn't a pull request
- **WHEN** a branch, or `main`, is pushed and no pull request is involved
- **THEN** the GitHub check checks no description

### Requirement: A pull request description the check can't read fails it
When a pull request's event payload has no description field, or one that is neither text nor empty (`null`), the
GitHub check SHALL fail under `pr-closes-issue`, saying it couldn't read the pull request's description and to re-run
the check, rather than treat the description as missing or as closing an issue.

#### Scenario: A payload with no description field
- **WHEN** the check runs for a pull request whose event payload has no `body` field
- **THEN** the GitHub check fails under `pr-closes-issue`, saying it couldn't read the description, and to re-run the
  check and tell the owner if it fails again

#### Scenario: A description that isn't text
- **WHEN** the check runs for a pull request whose event payload's `body` is a number
- **THEN** the GitHub check fails the same way
