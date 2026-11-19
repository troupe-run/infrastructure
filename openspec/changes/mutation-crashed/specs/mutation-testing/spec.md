## ADDED Requirements

### Requirement: A run's report names its crashed mutants
A mutation run's report SHALL record each crashed mutant as it records a survivor: its name, path, line and change,
and the tool's exit code where it gives one. The weekly run's summary SHALL list them with what each ended, so the
owner can decide on exclusions from them. No mutant SHALL be excluded without the owner.

#### Scenario: A mutant crashes its tests
- **WHEN** a mutant's tests die by a signal and mutmut records the mutant as crashed
- **THEN** the report lists it with its name, path, line, change and exit code, and the summary lists it as having
  ended only its own test process

#### Scenario: A crash that ends the run
- **WHEN** a mutant ends the unit's mutmut itself
- **THEN** the report has no entry for it, and the step says the run was killed or exited, as it does for any run
  that ends early

#### Scenario: A malformed list
- **WHEN** a report's module counts 2 crashed and lists 1 crashed mutant
- **THEN** reading the report fails, naming the module and both numbers
