# Spec Delta

## ADDED Requirements

### Requirement: One contributing guide covers every governed repository
The org's contributing guide SHALL apply to every repository that builds with the development workflow, and SHALL NOT
send a contributor to another repository's guide for the workflow, commit rules or milestones. What differs by
repository SHALL appear in it as a case for that repository. Setting up and running a repository SHALL stay in that
repository's README.

#### Scenario: A website contributor reads the org's guide
- **WHEN** someone contributing to website opens the org's contributing guide
- **THEN** it doesn't say website has a guide of its own, and it tells them website's licences and that website
  takes no sign-off

#### Scenario: The workflow names the commit rules
- **WHEN** someone reads the guide's workflow
- **THEN** it says commit messages are Conventional Commits and that the repository's check passes before every commit

### Requirement: The guide's sign-off cases match what each repository enforces
The guide SHALL name each governed repository whose pull requests require the `DCO` check as taking a sign-off, and
each governed repository that doesn't require it as taking none. A difference SHALL fail the repository's check,
naming the repository.

#### Scenario: A repository that requires DCO
- **WHEN** a repository's required checks include `DCO`
- **THEN** the guide names it among the repositories that take a sign-off

#### Scenario: The guide and the rulesets disagree
- **WHEN** a repository's required checks change to add or drop `DCO` and the guide isn't changed
- **THEN** the check fails, naming the repository and which way they disagree

### Requirement: The guide says how a fix from outside is carried
The guide SHALL tell a contributor that a pull request made outside the workflow, such as in GitHub's editor, fails
the `guard` check as expected, and that a maintainer carries it on a change branch of their own, credits its author
with `Co-authored-by:`, links it, and closes it when theirs merges.

#### Scenario: A fix made in GitHub's editor
- **WHEN** a contributor without the workflow opens a pull request and its `guard` check fails
- **THEN** the guide tells them that's expected and that a maintainer carries the fix and credits them
