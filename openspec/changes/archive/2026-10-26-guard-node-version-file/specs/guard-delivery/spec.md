# Spec Delta

## ADDED Requirements

### Requirement: The delivered guard check takes Node from the repository's .nvmrc
The `guard` workflow SHALL set up Node from the `.nvmrc` of the repository it runs in, when that repository has one,
and from the workflow's own pinned version only when it hasn't. No step of the workflow SHALL name a Node version as
an input, and the workflow SHALL NOT change or commit a repository's `.nvmrc`. The pin SHALL be declared in one place
in the workflow.

#### Scenario: A repository that keeps its Node version in .nvmrc
- **WHEN** the `guard` check runs in `website`, whose `.nvmrc` says `22`
- **THEN** it installs the OpenSpec CLI on Node 22, read from that `.nvmrc`

#### Scenario: A repository with no .nvmrc
- **WHEN** the `guard` check runs in `troupe` or this repository, neither of which has an `.nvmrc`
- **THEN** it installs the OpenSpec CLI on the workflow's pinned Node version, and the run's commits are unchanged

#### Scenario: The delivered workflow passes a rule against workflow-named Node versions
- **WHEN** a check reads every step of the delivered `.github/workflows/guard.yml`, ignoring each step's `if:`
- **THEN** every `actions/setup-node` step has `node-version-file: .nvmrc` and no `node-version` input, and no other
  step has a `node-version` input

#### Scenario: A change here that names a Node version again
- **WHEN** a commit in this repository gives a step of `.github/workflows/guard.yml` a `node-version` input
- **THEN** this repository's tests fail, naming the step, before the file can be delivered
