## ADDED Requirements

### Requirement: A mutation run uses only each unit's selected tests
Each mutmut unit SHALL name the tests a mutation run uses, a directory under its tests (troupe's: its unit tests).
The scheduled run and a pull request's report SHALL run only those. The unit's other tests and helpers SHALL stay
beside it, never mutated. A missing selection, one outside its tests, or a deselect outside it SHALL be refused. A
changed selection SHALL start the unit afresh, named.

#### Scenario: An integration test isn't run
- **WHEN** troupe's `troupe` unit is mutated
- **THEN** mutmut runs `packages/troupe/tests/unit`, and no test in `packages/troupe/tests/integration` runs

#### Scenario: The shared helpers stay importable and unmutated
- **WHEN** a unit test imports a helper kept in `packages/troupe/tests/`
- **THEN** the helper is found in mutmut's copy, and none of its lines is mutated

#### Scenario: A unit without a selection
- **WHEN** a mutmut unit in the settings has no `select`, or one that leaves its tests' directory
- **THEN** loading the settings fails, naming the unit and the field

#### Scenario: The selection changes
- **WHEN** a unit's state was saved with another selection
- **THEN** the unit starts afresh, the summary says its settings moved, and the run fails visibly
