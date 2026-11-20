## MODIFIED Requirements

### Requirement: A runaway mutant ends only its own tests
When the settings give a per-mutant memory cap, each process that tests a mutant SHALL run under it, so a mutant whose
tests allocate past it ends only those tests, and the run records it and goes on. The passes with no mutant SHALL run
without it. A cap that isn't null or a whole number in range SHALL be refused, naming the setting. The cap SHALL be
set from a recorded run's measured peaks, never by arithmetic on the cgroup's limit.

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

#### Scenario: The cap troupe runs under
- **WHEN** troupe's weekly run reads the settings
- **THEN** each mutant's process is capped at 2,048 MB, set from dry run 44693481824's peaks (mutmut's own 1,111 MB
  and the largest ordinary mutant's 1,270 MB of virtual size, plus half, rounded up to 256 MB)
