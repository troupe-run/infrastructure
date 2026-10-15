## MODIFIED Requirements

### Requirement: Checks pass before a commit
A commit SHALL be refused unless the repository's full check (`scripts/check.py`) passes on the work being
committed. The exception: when the repository declares which paths need no check and which need only named scopes of
it, and every staged path is declared, the commit needs only what those paths need. What runs is announced.

#### Scenario: A failing check
- **WHEN** a contributor commits while a gate fails
- **THEN** the commit is refused and the message names the failing gate

#### Scenario: The check is never silent and never endless
- **WHEN** the check, or a scope of it, runs before a commit
- **THEN** it is announced before it starts, and its output appears as it runs
- **AND** if it is still running after a set timeout (default 10 minutes, defined in one place), it is stopped
  and the commit is refused with a message naming the timeout

#### Scenario: Only skipped paths are staged
- **WHEN** the repository's `scripts/check-paths.toml` skips `openspec/**`, and a commit stages only files under
  `openspec/`, including a change moved into `openspec/changes/archive/`
- **THEN** no check runs, and the commit goes ahead if the other commit rules are met
- **AND** the guard says the check was skipped, naming the skipped paths and `scripts/check-paths.toml`

#### Scenario: Only one scope's paths are staged
- **WHEN** the declaration has a scope `docs` covering `docs/**` and skips `openspec/**`, and a commit stages files
  under `docs/`, with or without files under `openspec/`
- **THEN** `scripts/check.py --scope docs` runs instead of the full check, and the guard says so

#### Scenario: Two scopes' paths are staged
- **WHEN** the declaration has scopes `api` and `docs`, and a commit stages a path in each
- **THEN** `scripts/check.py --scope api --scope docs` runs, with the names sorted, instead of the full check

#### Scenario: A failing scope
- **WHEN** a scope runs before a commit and one of its gates fails
- **THEN** the commit is refused and the message names the failing gate

#### Scenario: A path the declaration doesn't name is staged
- **WHEN** a commit stages any path that is in neither the skip list nor a scope
- **THEN** the full check runs, as for any commit

#### Scenario: A file moved out of a read path
- **WHEN** the declaration skips `openspec/**`, and a commit moves a file from outside `openspec/` into it
- **THEN** the full check runs, because the file's old path counts as staged too

#### Scenario: No declaration
- **WHEN** the repository has no `scripts/check-paths.toml` staged, and a commit stages only files under `openspec/`
- **THEN** the full check runs, as for any commit

#### Scenario: The declaration itself is staged
- **WHEN** a commit stages `scripts/check-paths.toml`, whatever it declares
- **THEN** the full check runs

#### Scenario: A malformed declaration
- **WHEN** the staged `scripts/check-paths.toml` can't be parsed, has an unknown version, table or key, lists an
  entry that is neither an exact path nor a directory written `dir/**`, has two groups whose entries overlap, or names
  a scope with a bad or reserved name (`none`, `full`)
- **THEN** the commit is refused under `commit-checks`, and the message names the file, what's wrong with it and how
  to fix it

#### Scenario: Unstaged changes still refuse a skippable commit
- **WHEN** tracked files have unstaged changes, and the commit stages only skipped paths
- **THEN** the commit is refused for the unstaged changes, as before

## ADDED Requirements

### Requirement: CI reads the same declaration
The guard SHALL offer CI the same decision as the commit hook, from the same declaration: given a list of changed
paths, it says whether nothing, which scopes, or the full check must run, and gives the arguments for
`scripts/check.py`. An empty list SHALL mean the full check, and a malformed declaration SHALL fail with the commit
hook's message.

#### Scenario: Only skipped paths changed
- **WHEN** CI asks with changed paths that are all skipped
- **THEN** the guard answers `none`

#### Scenario: Only scoped and skipped paths changed
- **WHEN** CI asks with changed paths in the scopes `docs` and `api`, and possibly skipped paths
- **THEN** the guard answers `api,docs`, and the arguments `--scope api --scope docs`

#### Scenario: Any other path changed
- **WHEN** CI asks with changed paths that include one the declaration doesn't name, or the repository has no
  declaration
- **THEN** the guard answers `full`, with no arguments

#### Scenario: No changed paths
- **WHEN** CI asks with an empty list of changed paths
- **THEN** the guard answers `full`

#### Scenario: A malformed declaration in CI
- **WHEN** CI asks while the repository's declaration is malformed
- **THEN** the guard fails, naming the file, what's wrong and the fix, and gives no answer
