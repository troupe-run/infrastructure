## MODIFIED Requirements

### Requirement: A mutant can't stop the runner or the rest of the run
A mutation run SHALL run in a PID namespace and a cgroup of its own, as the runner's user and with the step's
environment, under a memory and a task limit; and each mutant's tests SHALL run in a session of their own. A mutant
that signals its own group ends only its tests, and is counted as crashed; one that signals every process, or runs the
runner out of memory, ends at most the run.

#### Scenario: A mutant kills its own process group
- **WHEN** a mutant makes the code under test send SIGKILL to its own process group
- **THEN** only that mutant's test process dies, the mutant is counted as crashed, and the run, the job and its log
  carry on

#### Scenario: The run itself dies
- **WHEN** the whole mutation run is killed
- **THEN** the step fails with the run's exit status, and the job still uploads its readings and keeps its log

#### Scenario: A mutant signals every process
- **WHEN** a mutant makes the code under test send SIGKILL to every process it may (`kill(-1, …)`)
- **THEN** only processes inside the run's namespace die (the run's first process, its init, is spared), no process
  outside it does, the step reports how the run ended, and the job and its log carry on

#### Scenario: The run runs out of memory
- **WHEN** the run's processes use more memory than its limit
- **THEN** the kernel ends the run, the step fails saying it ran out of memory and naming the limit, and the job and
  its log carry on
