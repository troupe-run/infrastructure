## ADDED Requirements

### Requirement: A runaway mutant ends only its own tests
When the settings give a per-mutant memory cap, each process that tests a mutant SHALL run under it, so a mutant whose
tests allocate past it ends only those tests, and the run records it and goes on. The passes with no mutant SHALL run
without it. A cap that isn't null or a whole number in range SHALL be refused, naming the setting.

#### Scenario: A mutant allocates without bound
- **WHEN** a mutant makes its tests allocate memory past the cap
- **THEN** only that mutant's test process fails, the mutant is counted as killed or crashed (and named if crashed),
  and the run carries on to the next mutant

#### Scenario: The passes with no mutant
- **WHEN** mutmut runs its stats and clean passes
- **THEN** they run without the cap, as before

#### Scenario: No cap
- **WHEN** the setting is null
- **THEN** no mutant's process is capped, and the run behaves as before

#### Scenario: A malformed cap
- **WHEN** the setting is a string, a fraction, or out of range
- **THEN** reading the settings fails, naming the setting, its value and the range

### Requirement: A run records the memory its passes peak at
For each unit, a run SHALL log the peak virtual size and peak resident size of mutmut's own process, where its stats
and clean passes run, and of the largest of its mutants' test processes, so a cap can be set from measured peaks.

#### Scenario: A unit's run ends
- **WHEN** a unit's mutmut run ends, whether or not it finished
- **THEN** the log has a `memory:` line for mutmut's own process and for the largest mutant processes, each with
  its peak virtual and resident size, and the mutant's name where there is one

#### Scenario: Nothing was recorded
- **WHEN** no process recorded its peaks (as off Linux, with no /proc)
- **THEN** the run logs that no peaks were recorded and carries on
