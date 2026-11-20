## ADDED Requirements

### Requirement: Commit text that release notes would read as markup is refused
A commit message SHALL be refused under `commit-message` when its subject, or a `BREAKING CHANGE:` or
`BREAKING-CHANGE:` note, contains text that release-please's notes parser reads as HTML markup (`<!--`, or a tag
such as `<NAME>`), or an entity that decodes to it (`&lt`, `&#`, `&amp`). The refusal quotes the text, and says to
write it without angle brackets and that backticks don't protect it.

#### Scenario: A placeholder in angle brackets
- **WHEN** a contributor commits with the message `fix(runtimes): the actor's model beats TROUPE_RUNTIME_<NAME>_MODEL`
- **THEN** the commit is refused under `commit-message`, quoting `<NAME>` and suggesting `TROUPE_RUNTIME_{NAME}_MODEL`

#### Scenario: The same text in backticks
- **WHEN** a contributor commits with the message `` fix: read `Vec<u8>` ``
- **THEN** the commit is refused, and the message says backticks don't protect it

#### Scenario: A breaking-change note
- **WHEN** a commit's message has the footer `BREAKING CHANGE: runners now read <config>`
- **THEN** the commit is refused under `commit-message`, quoting `<config>`

#### Scenario: An entity for an angle bracket
- **WHEN** a commit's subject says `read &lt;NAME&gt;`
- **THEN** the commit is refused under `commit-message`, quoting `&lt`

#### Scenario: Angle brackets that aren't markup
- **WHEN** a commit's subject says `a < b`, `a <= b`, `1<2`, `<3` or `a -> b`, or its body or trailers hold
  `<NAME>` or an address such as `Co-Authored-By: Claude <noreply@anthropic.com>`
- **THEN** the commit-message rule doesn't refuse it

#### Scenario: The same text in a pushed commit or a pull request's title
- **WHEN** a branch carrying such a commit is pushed, or a pull request's title contains such text
- **THEN** the push, or the `guard` check, is refused under `commit-message`, naming the commit, or the title, and
  quoting the text

## MODIFIED Requirements

### Requirement: Commit messages are checked before a push
A push SHALL be refused while any commit it would send, on any branch, has a message that isn't a Conventional
Commit or holds text release notes would read as markup, or changes a file under `protocol/schemas/` under a type
that releases nothing. The refusal names each such commit.

#### Scenario: Pushing a non-conventional commit
- **WHEN** a contributor pushes a branch carrying a commit whose first line is `Add a thing`
- **THEN** the push is refused, naming that commit and the expected form

#### Scenario: Pushing conventional commits
- **WHEN** every commit being pushed is a Conventional Commit
- **THEN** the push goes ahead

#### Scenario: Pushing a schema change reworded after it was made
- **WHEN** a contributor pushes a commit that changes a file under `protocol/schemas/`, whose message was amended or
  reworded to `chore: tidy` after the commit was made
- **THEN** the push is refused under `schema-commit-type`, naming that commit and its schema files
