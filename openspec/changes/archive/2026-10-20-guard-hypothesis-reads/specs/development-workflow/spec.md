## MODIFIED Requirements

### Requirement: Test tags cover what each test reads
Whenever a repository's tests run, a test SHALL fail if it reads a file under a scope's paths without that scope's
tag, or reads a file under a skipped path. Only files inside the repository count. The message SHALL name the test,
the file, and the tag to add or the skip entry it contradicts. A file Hypothesis opens to collect constants from a
module's source SHALL NOT count as the test's read.

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

#### Scenario: Hypothesis reads a module's source for its own constants
- **WHEN** a test tagged with scope `pkg` imports a module under `pkg/`, and then an untagged Hypothesis test draws,
  so Hypothesis reads that module's source to collect constants
- **THEN** the untagged test doesn't fail: the read is Hypothesis's own, not the test's

#### Scenario: A Hypothesis test that reads a scope's path itself
- **WHEN** an untagged Hypothesis test opens a file under `pkg/` in its own body
- **THEN** it fails as any other test does, naming the file and the `pkg` tag
