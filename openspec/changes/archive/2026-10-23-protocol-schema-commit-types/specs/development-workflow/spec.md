# Spec Delta

## ADDED Requirements

### Requirement: Schema changes use a commit type that releases
In a governed repository with a `protocol/schemas/` directory, a commit that changes, adds or removes a file under it
SHALL be refused unless its type releases: `feat`, `fix`, `perf` or `revert`, or any type marked breaking. The
refusal is under `schema-commit-type`, and names the schema files and the allowed types.

#### Scenario: A schema change under a type that releases nothing
- **WHEN** a contributor commits a change to `protocol/schemas/error.schema.json` with the message
  `docs(protocol): describe the error codes`
- **THEN** the commit is refused under `schema-commit-type`, naming `protocol/schemas/error.schema.json` and the
  types `feat`, `fix`, `perf` and `revert`, and saying that a breaking change of any type is allowed

#### Scenario: A schema change under a releasing type
- **WHEN** a contributor commits a change to a file under `protocol/schemas/` with the message
  `feat(protocol): add the notice schema`, or with type `fix`, `perf` or `revert`
- **THEN** the commit is made

#### Scenario: A breaking schema change under any type
- **WHEN** a contributor commits a change to a file under `protocol/schemas/` with the message
  `refactor(protocol)!: rename the run fields`, or with a `BREAKING CHANGE:` or `BREAKING-CHANGE:` footer
- **THEN** the commit is made

#### Scenario: Other files under protocol/
- **WHEN** a commit with the message `docs(protocol): explain versioning` changes only `protocol/README.md`,
  `protocol/CHANGELOG.md` or other files outside `protocol/schemas/`
- **THEN** the schema rule doesn't refuse it

#### Scenario: A repository with no protocol schemas
- **WHEN** a commit of any accepted type is made in a governed repository that has no `protocol/schemas/` directory
- **THEN** the schema rule doesn't refuse it

#### Scenario: Only the files being committed count
- **WHEN** a contributor commits with `git commit -a` or `git commit <path>`, or with schema changes left unstaged
- **THEN** the rule judges the files that commit will contain, and no others

#### Scenario: A fixup names the commit it fixes
- **WHEN** a `fixup!`, `squash!` or `amend!` commit changes a schema
- **THEN** the rule judges the type of the commit it names

## MODIFIED Requirements

### Requirement: Commit messages are checked before a push
A push SHALL be refused while any commit it would send, on any branch, has a message that isn't a Conventional
Commit, or changes a file under `protocol/schemas/` under a type that releases nothing. The refusal names each such
commit.

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

### Requirement: The rules are re-checked on GitHub
For every push to any branch and for every pull request, a GitHub check SHALL re-apply the git-level rules to the
commits involved: every commit message is a Conventional Commit, the branch matches an OpenSpec change (for any
branch other than `main`, except a release branch in a repository that reserves its name for the release App), and no
archived change has an unticked task. It applies the same rules as the git hooks, so a commit that skipped the local
hooks is still caught.

#### Scenario: A push that skipped the local hooks
- **WHEN** a branch is pushed carrying a commit with a non-conventional message that was made with `--no-verify`
- **THEN** the GitHub check for that push fails and names the commit

#### Scenario: A schema change that skipped the local hooks
- **WHEN** a pull request carries a commit made with `--no-verify` that changes a file under `protocol/schemas/` with
  the message `test: cover the schema`
- **THEN** the GitHub check fails under `schema-commit-type`, naming the commit and its schema files

#### Scenario: A pull request from a branch with no matching change
- **WHEN** a pull request's branch has no matching OpenSpec change
- **THEN** the GitHub check fails and names the rule

#### Scenario: A Dependabot pull request in a governed repository
- **WHEN** a pull request in `troupe-run/troupe`, `troupe-run/infrastructure` or `troupe-run/website` comes from a
  branch named `dependabot/<ecosystem>/<package>-<version>`, which has no matching OpenSpec change
- **THEN** the GitHub check fails on the branch-change rule: no exemption covers a Dependabot branch
