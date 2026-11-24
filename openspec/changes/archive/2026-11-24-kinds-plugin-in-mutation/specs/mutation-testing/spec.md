## MODIFIED Requirements

### Requirement: A repository's mutation run finds the files its tests read
A mutation run SHALL let a repository's tests find the files they read beside their source, wherever the tool's copy
puts them, and SHALL keep the repository's own pytest options apart from those that can't work in the copy. A test that
can't run under the tool at all SHALL be deselected in the settings, with its reason.

#### Scenario: troupe's tests find the repository's files
- **WHEN** troupe's `troupe` package is mutated and a test reads `plugins/runner-anthropic/fixtures`, counting
  directories up from its own file
- **THEN** it finds the directory, as it does outside the run

#### Scenario: troupe's own pytest plugins load
- **WHEN** troupe's package is mutated
- **THEN** its tests run with the plugins troupe's pytest options load, without `--strict-markers`, the guard's tag
  plugin and troupe's kinds plugin, which can't find their declarations or suites from the copy

#### Scenario: A package's tests find a sibling package
- **WHEN** `troupe-store-text` is mutated and a test points a child process at `packages/troupe/tests`, counting two
  directories up from its own file
- **THEN** the child finds troupe's tests, as it does outside the run
