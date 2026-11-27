# Spec Delta

## ADDED Requirements

### Requirement: A scheduled run re-tests the results its changed tests could change
A scheduled run SHALL re-test every kept result a test change since its state was saved could change: the functions
reached by a changed or removed test, by a test whose helpers or conftest changed, and by a new test. A run that can't
tell what changed SHALL count every test as changed. A night with no test change SHALL carry the kept results. The
summary SHALL say, per unit, how many results were cleared for changed tests.

#### Scenario: A pull request adds a module's first unit tests
- **WHEN** the last run kept `troupe.cli.init`'s mutants as survived or reached by no test, and a new test file now
  reaches them
- **THEN** this run tests those mutants again, the score counts the new tests, and the summary says how many results
  it cleared for them

#### Scenario: An edited test
- **WHEN** a test file changed since the state was saved, and its tests reached a function whose mutants were killed
- **THEN** that function's mutants are tested again, and a function no changed test reached keeps its results

#### Scenario: A changed helper
- **WHEN** a helper under the unit's tests changed, and a test file imports it through another helper
- **THEN** the functions that test file's tests reach are tested again

#### Scenario: State saved without a record of its tests
- **WHEN** the restored state has no fingerprint of the unit's tests
- **THEN** every test counts as changed, and the summary says so

#### Scenario: A night with no test change
- **WHEN** no file under the unit's tests changed and no test was added
- **THEN** no result is cleared for tests, mutmut runs once, and only changed functions are tested again

#### Scenario: The budget runs out before the new tests' results
- **WHEN** a test is added and the budget stops the run before mutmut runs again
- **THEN** the results it cleared are saved cleared, and the next run tests them
