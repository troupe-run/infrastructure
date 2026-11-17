# Spec Delta

## ADDED Requirements

### Requirement: The quality-gate module is delivered with the guard's files
The module that measures the quality gates (spec: quality-gates) SHALL be one of the delivered files, so troupe,
website and this repository measure coverage, complexity and advisories the same way. Each repository's
`quality-gates.toml` SHALL NOT be delivered: its thresholds and baselines are its own.

#### Scenario: The gate module reaches troupe and website
- **WHEN** a change to `scripts/quality_gates.py` is merged here and its plan applied
- **THEN** troupe and website each get a delivery commit with the new content, and their delivered lists name it

#### Scenario: A repository's thresholds stay its own
- **WHEN** website's `quality-gates.toml` sets a different complexity limit from this repository's
- **THEN** no plan shows a change to it, and website's check uses its own limit
