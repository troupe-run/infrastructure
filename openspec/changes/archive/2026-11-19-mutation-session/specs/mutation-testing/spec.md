## ADDED Requirements

### Requirement: A mutant can't stop the runner or the rest of the run
A mutation run SHALL run in a process session of its own, apart from the runner agent's, and each mutant's tests
SHALL run in a session of their own, so a mutant that signals its own process group ends only its own tests. Such a
mutant SHALL be counted as crashed, and the run SHALL go on to the next mutant.

#### Scenario: A mutant kills its own process group
- **WHEN** a mutant makes the code under test send SIGKILL to its own process group
- **THEN** only that mutant's test process dies, the mutant is counted as crashed, and the run, the job and its log
  carry on

#### Scenario: The run itself dies
- **WHEN** the whole mutation run is killed
- **THEN** the step fails with the run's exit status, and the job still uploads its readings and keeps its log
