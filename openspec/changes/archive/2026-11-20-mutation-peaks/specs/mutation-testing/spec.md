## MODIFIED Requirements

### Requirement: A run records the memory its passes peak at
For each unit, a run SHALL log the peak virtual size and peak resident size of mutmut's own process, where its stats
and clean passes run, and of the largest of its mutants' test processes, so a cap can be set from measured peaks. In
CI the peaks SHALL be kept in a file the job uploads, and the summary printed from outside the contained run, so a
run its cgroup kills still logs it.

#### Scenario: A unit's run ends
- **WHEN** a unit's mutmut run ends, whether or not it finished
- **THEN** the log has a `memory:` line for mutmut's own process and for the largest mutant processes, each with
  its peak virtual and resident size, and the mutant's name where there is one

#### Scenario: Nothing was recorded
- **WHEN** no process recorded its peaks (as off Linux, with no /proc)
- **THEN** the run logs that no peaks were recorded and carries on

#### Scenario: The run is killed
- **WHEN** the contained run is killed, as by its cgroup's OOM killer, after some of its processes recorded peaks
- **THEN** the step still logs the `memory:` lines for each unit reached, and the job uploads the peaks file
