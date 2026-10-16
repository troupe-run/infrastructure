# Spec Delta

## MODIFIED Requirements

### Requirement: Guardrails behave the same on every platform
Every rule in this capability SHALL behave the same on Linux, macOS and Windows, and on every Python version troupe
supports.

#### Scenario: The guardrail tests on each platform
- **WHEN** the guardrail tests run on Linux, macOS and Windows
- **THEN** they pass on each

#### Scenario: The guardrail tests on each supported Python version
- **WHEN** the guardrail tests run on each Python version troupe supports (3.12 to 3.15 today), on each of Linux,
  macOS and Windows
- **THEN** they pass on each, and a pull request here can't merge until every one of those runs has passed
