## ADDED Requirements

### Requirement: Delivered Python type-checks for Windows before it's delivered
This repository's check SHALL type-check every Python file it delivers to another repository (named in
`tofu/guard_delivery.tf`) as Windows sees it, on every OS the check runs on, so code that only type-checks on POSIX
fails here and never reaches a receiving repository's Windows check.

#### Scenario: A delivered file uses a POSIX-only module unguarded
- **WHEN** a delivered file uses `resource.setrlimit` without narrowing on `sys.platform`
- **THEN** this repository's check fails, naming the file and line, before any delivery

#### Scenario: A file delivered later
- **WHEN** a Python file is added to the delivered lists in `tofu/guard_delivery.tf`
- **THEN** the check type-checks it for Windows too, with no second list to update

#### Scenario: The mutation plugin on Windows
- **WHEN** troupe's Windows check type-checks the delivered `scripts/mutation_children.py`
- **THEN** it passes, and the per-mutant cap does nothing on Windows, where no mutation run happens
