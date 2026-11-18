## MODIFIED Requirements

### Requirement: Every threshold lives in the repository's gate config
Each governed repository SHALL declare its gates' thresholds, and, if it measures coverage, its coverage packages and
their baselines, in one file, `quality-gates.toml` at its root, and in no other place. The file SHALL be read strictly:
an unknown table or key, a value of the wrong type, a threshold out of range, or a package whose paths overlap
another's SHALL fail the check, naming the file, the key and what's valid. A missing file SHALL fail the check too: a
gate is never skipped because its config is absent. `[coverage]` alone is optional: a repository that infrastructure's
list doesn't name for coverage leaves it out (spec: mutation-testing).

#### Scenario: A misspelt key
- **WHEN** `quality-gates.toml` sets `[complexity] block_abve = 25`
- **THEN** the check fails, naming `complexity.block_abve` as unknown and listing the keys `[complexity]` takes

#### Scenario: No config
- **WHEN** a governed repository's check runs and `quality-gates.toml` doesn't exist
- **THEN** the check fails, saying the file is missing and what it must declare

#### Scenario: No coverage table
- **WHEN** a repository's `quality-gates.toml` has no `[coverage]` table and its coverage leg runs
- **THEN** no coverage is measured or judged, the leg says coverage isn't measured in this repository, and its other
  gates run as usual
