## ADDED Requirements

### Requirement: A collection read counts only for the tests collected under it
A file opened while a test module, or a directory or class of tests, is being collected SHALL count as a read of the
tests under it, and of no other test. This SHALL hold however the run selects its tests (no arguments, paths, or node
ids) and whether or not it runs in parallel workers. A test's own collection reads, such as a module-level read or
parameters built from a file, SHALL still count for it.

#### Scenario: Tests from two scopes selected by node id
- **WHEN** scopes `alpha` and `beta` each have a `tests` directory, one of them with a `conftest.py`, and a run
  selects one clean test from each by node id, in one process or in parallel workers
- **THEN** both tests pass, and the guard reports nothing: neither is charged with the other module's source,
  compiled bytecode or conftest

#### Scenario: An untagged read in a selection by node id
- **WHEN** the same selection also names a test under `alpha`'s directory that reads `docs/a.md`, which only scope
  `docs` covers
- **THEN** that test fails, naming `docs/a.md` and the `docs` tag, and the other selected tests pass

#### Scenario: A module-level read in a selection by node id
- **WHEN** a module under `alpha`'s directory reads `docs/a.md` at import, and a run selects one of its tests and a
  test under `beta`'s directory by node id
- **THEN** the selected test from that module fails for reading `docs/a.md`, and the test under `beta`'s directory
  passes
