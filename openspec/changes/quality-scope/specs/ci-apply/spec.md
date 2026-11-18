## MODIFIED Requirements

### Requirement: One CI leg runs the coverage and audit gates
This repository's `check` job SHALL run on Linux with Python 3.15, and SHALL run the dependency-audit gate (spec:
quality-gates) as well as the rest of the check, against the base revision of the pull request or merge group it
tests. It SHALL run the coverage gate only when infrastructure's list names this repository for coverage (spec:
mutation-testing); today it doesn't. The guard's legs SHALL include Linux with Python 3.12, so every supported Python
version is still tested on Linux. A scoped check SHALL NOT run the coverage gate, since its tests are a subset.

#### Scenario: A ready pull request's check
- **WHEN** a ready pull request changing `scripts/oob.py` is tested
- **THEN** the `check` job runs the full check on Python 3.15, including the complexity and audit gates, against the
  pull request's base, and says coverage isn't measured in this repository

#### Scenario: A scoped check skips coverage
- **WHEN** a pull request changes only `tofu/dns.json`
- **THEN** the `check` job runs the scoped check, its complexity and audit gates, and measures no coverage

#### Scenario: Linux 3.12 is still tested
- **WHEN** a pull request runs the guard's legs
- **THEN** one of them runs on Linux with Python 3.12
