## ADDED Requirements

### Requirement: The guard is delivered to troupe and the website
The guard SHALL be delivered to `troupe` and `website`, and to no other repository. This repository is governed too,
as the guard's source. The list of repositories that receive it SHALL be declared in one place.

#### Scenario: Both governed repositories receive the guard
- **WHEN** the managed state is read after an apply
- **THEN** `troupe` and `website` each hold every delivered file with its source content, and no other repository
  holds any

#### Scenario: The website's delivered list names its files
- **WHEN** the website's `.github/guard-delivery.json` is read
- **THEN** it names this repository as the source and lists exactly the files delivered to it

### Requirement: A repository receives the guard only once it can run it
A repository SHALL be added to the guard's targets only after its `main` holds what the guard needs to run there: an
`openspec/` directory, a `scripts/check.py` that runs its checks, and contributor docs that say what to install. None
of the delivered files SHALL already exist in it.

#### Scenario: The website's first commit after delivery is checked
- **WHEN** the guard has been delivered to the website and a contributor commits on a branch named after an OpenSpec
  change in it
- **THEN** the commit hook runs the website's `scripts/check.py` and allows the commit only if it passes

#### Scenario: A delivery never overwrites a file the repository wrote
- **WHEN** a plan adds a repository to the guard's targets and that repository already has a file at a delivered
  path
- **THEN** the apply fails for that file rather than replacing it, and the owner resolves it in the repository first
