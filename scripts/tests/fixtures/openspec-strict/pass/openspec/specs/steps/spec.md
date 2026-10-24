# steps Specification

## Purpose
How a runner reports the steps of a run to the client that started it.

## Requirements
### Requirement: Runs start
The runner SHALL start a run when asked.

#### Scenario: Start
- **WHEN** asked
- **THEN** it starts

### Requirement: Runs stop
The runner SHALL stop a run when asked.

#### Scenario: Stop
- **WHEN** asked
- **THEN** it stops

### Requirement: Steps are reported
The runner SHALL report each step.

#### Scenario: Report
- **WHEN** a step ends
- **THEN** it is reported
