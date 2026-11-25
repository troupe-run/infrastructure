## ADDED Requirements

### Requirement: A run's report renders its survivors' diffs in one process
After mutmut stops, the run SHALL render every survivor's and crashed mutant's diff in one process of mutmut's own
interpreter, with mutmut's own functions, producing exactly what `mutmut show` prints. A render that fails, isn't
JSON, or leaves a mutant out SHALL fail the run, never report a blank diff.

#### Scenario: Thousands of survivors
- **WHEN** a unit ends with thousands of survivors
- **THEN** their diffs come from one render, and the report is written within the job's time

#### Scenario: A render leaves a mutant out
- **WHEN** the render's output lacks a mutant the report reads
- **THEN** the run fails, naming the mutant
