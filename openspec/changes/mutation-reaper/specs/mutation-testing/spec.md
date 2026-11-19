## ADDED Requirements

### Requirement: The contained run reaps its orphans
The mutation run's PID namespace SHALL have an init that reaps every process reparented to it, so a process the run's
code kills doesn't stay a zombie, and the run's exit status, whether a plain status or a signal, SHALL reach the step
unchanged.

#### Scenario: A killed grandchild
- **WHEN** code under test starts a child, which starts a grandchild and exits, and then kills the grandchild
- **THEN** the grandchild is reaped within moments, as it is outside the namespace, so a test that waits for it to be
  gone passes

#### Scenario: The run's status passes through
- **WHEN** the run exits with status 3, or is killed by SIGKILL
- **THEN** the step sees status 3, or 137, as before
