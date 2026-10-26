# Spec Delta

## ADDED Requirements

### Requirement: A Python tooling dependency update isn't planned
A pull request that changes only the Python tooling's dependency files at the repository root (`pyproject.toml` and
`uv.lock`), with or without other files OpenTofu never reads, SHALL NOT be planned and SHALL NOT ask the owner for an
approval. This SHALL hold only while no step of the plan or apply runs in the Python project's environment. The
provider lockfile SHALL be planned, since it changes what OpenTofu runs.

#### Scenario: A Python tooling bump isn't planned
- **WHEN** a pull request changes only `uv.lock`, or `uv.lock` and `pyproject.toml`
- **THEN** its plan job is skipped, no approval is requested, and the skipped job counts as passed

#### Scenario: A provider lockfile bump is planned
- **WHEN** a pull request changes `tofu/.terraform.lock.hcl`, alone or with `uv.lock`
- **THEN** it is planned like any other, and needs the owner's approval of its plan run

#### Scenario: Only the root files are skipped
- **WHEN** a pull request changes a `pyproject.toml` or `uv.lock` anywhere but the repository root
- **THEN** it is planned

#### Scenario: A plan step that uses the project's environment
- **WHEN** a step of the `tofu` workflow runs a script in the Python project's environment rather than without it
- **THEN** the repository's tests fail, naming the step, until the step runs without the project or the Python files
  stop being skipped
