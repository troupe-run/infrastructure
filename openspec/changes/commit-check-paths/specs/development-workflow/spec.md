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

#### Scenario: Paths in two scopes are staged
- **WHEN** the declaration has scopes `api` and `docs`, and a commit stages a path in each
- **THEN** `scripts/check.py --scope api --scope docs` runs, with the names sorted, instead of the full check

#### Scenario: A path in two overlapping scopes is staged
- **WHEN** the declaration has a scope `blah` covering `path1/**` and `another/**`, and a scope `blech` covering
  `path1/**`, and a commit stages `path1/blah.py`
- **THEN** `scripts/check.py --scope blah --scope blech` runs

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
  entry that is neither an exact path nor a directory written `dir/**`, has an entry in the skip list that overlaps
  an entry in a scope, or names a scope outside `[a-z][a-z0-9_]*` or with a reserved name (`none`, `full`)
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

### Requirement: A scope narrows only the tests
Given one or more scopes, a repository's check SHALL run every gate it runs for the full check, and SHALL narrow only
its tests, to those tagged with any of the scopes. It SHALL refuse a scope its declaration doesn't list.

#### Scenario: A scoped check
- **WHEN** `scripts/check.py --scope docs` runs in a repository that declares the scope `docs`
- **THEN** every gate runs, and the tests that run are exactly those tagged `docs`

#### Scenario: Two scopes
- **WHEN** `scripts/check.py --scope api --scope docs` runs
- **THEN** the tests that run are those tagged `api` or `docs`

#### Scenario: An undeclared scope
- **WHEN** `scripts/check.py --scope nope` runs and the declaration lists no scope `nope`
- **THEN** the check fails before running any gate, naming the scope and `scripts/check-paths.toml`

#### Scenario: A scope no test is tagged with
- **WHEN** `scripts/check.py --scope docs` runs, every other gate passes, and no test is tagged `docs`
- **THEN** the check passes, and says that no test is tagged `docs`, so there was nothing to test

### Requirement: Test tags cover what each test reads
Whenever a repository's tests run, a test SHALL fail if it reads a file under a scope's paths without that scope's
tag, or reads a file under a skipped path. Only files inside the repository count. The message SHALL name the test,
the file, and the tag to add or the skip entry it contradicts.

#### Scenario: A test reads a scope's path without its tag
- **WHEN** the declaration has a scope `docs` covering `docs/**`, and a test without the `docs` tag reads
  `docs/runs.md`
- **THEN** that test fails, naming `docs/runs.md` and saying to tag it `docs`

#### Scenario: A test reads a path in two scopes
- **WHEN** scopes `blah` and `blech` both cover `path1/**`, and a test tagged only `blah` reads `path1/x.json`
- **THEN** that test fails, saying to tag it `blech` too

#### Scenario: A test reads a skipped path
- **WHEN** the declaration skips `openspec/**`, and any test reads a file under `openspec/` in the repository
- **THEN** that test fails, naming the file and the skip entry, since the skip would let a change to it go untested

#### Scenario: Tags that cover the reads
- **WHEN** every file a test reads in the repository is in no group, or in scopes the test is tagged with
- **THEN** the tag check doesn't fail it

#### Scenario: Files outside the repository
- **WHEN** a test reads files in a temporary directory that its own fixture created
- **THEN** those reads don't count
