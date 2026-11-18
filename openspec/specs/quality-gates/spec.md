# quality-gates Specification

## Purpose
The merge gates every governed repository's check runs beyond its linters and tests: branch coverage that can't fall,
complexity that can't grow past a limit, and dependencies with no fixable high-severity advisory. Their thresholds
live in one config file per repository, and a weekly report covers the advisories no gate blocks on.

## Requirements

### Requirement: Every threshold lives in the repository's gate config
Each governed repository SHALL declare its gates' thresholds, its coverage packages and their baselines in one file,
`quality-gates.toml` at its root, and in no other place. The file SHALL be read strictly: an unknown table or key, a
value of the wrong type, a threshold out of range, or a package whose paths overlap another's SHALL fail the check,
naming the file, the key and what's valid. A missing file SHALL fail the check too: a gate is never skipped because
its config is absent.

#### Scenario: A misspelt key
- **WHEN** `quality-gates.toml` sets `[complexity] block_abve = 25`
- **THEN** the check fails, naming `complexity.block_abve` as unknown and listing the keys `[complexity]` takes

#### Scenario: No config
- **WHEN** a governed repository's check runs and `quality-gates.toml` doesn't exist
- **THEN** the check fails, saying the file is missing and what it must declare

### Requirement: A package's coverage can't drop below its baseline
On its coverage leg, a repository's check SHALL measure branch coverage (covered statements and branches over all
statements and branches) for each package its config declares, and SHALL fail when a package with a baseline measures
below it by more than the config's tolerance. A package with no baseline SHALL fail below the config's floor. Tests'
own files SHALL NOT be measured.

#### Scenario: Coverage drops
- **WHEN** a pull request deletes the tests for a branch in a package whose baseline is 90.0% and it then measures
  89.2%, with a tolerance of 0.2
- **THEN** the coverage leg fails, naming the package, 90.0%, 89.2% and the difference

#### Scenario: A new package
- **WHEN** a pull request adds a package with no baseline, which measures below the floor
- **THEN** the coverage leg fails, naming the package, the floor and the measurement

### Requirement: The coverage leg reports every package
The coverage leg SHALL print, for every declared package, its baseline or the floor, its measurement and the
difference, whether or not the gate fails. A baseline SHALL change only by an edit to the config.

#### Scenario: Coverage rises
- **WHEN** a package measures 2 points above its baseline
- **THEN** the gate passes and the report says by how much the baseline could be raised; the baseline in the config
  doesn't change by itself

### Requirement: Every measured source file belongs to a package
On its coverage leg, a repository's check SHALL fail when a measured source file is under no package its config
declares, so new code can't sit outside every baseline and floor.

#### Scenario: Code outside every package
- **WHEN** a pull request adds a source file under a path no declared package covers
- **THEN** the coverage leg fails, naming the file and saying to add it to a package in `quality-gates.toml`

### Requirement: A change can't add or worsen a function above the complexity limit
Every run of a repository's check, local or in CI, SHALL measure the cyclomatic complexity of each function the work
adds or edits, compared with a base revision. It SHALL fail when such a function's complexity is above the config's
limit and the function is new, or is more complex than at the base. A function already above the limit that a change
edits without making more complex SHALL pass. Paths the config excludes SHALL NOT be measured.

#### Scenario: A new complex function
- **WHEN** a pull request adds a function whose complexity is 31 and the limit is 25
- **THEN** the check fails, naming the file, the function, 31 and the limit

#### Scenario: An old complex function made worse
- **WHEN** a pull request adds a branch to a function whose complexity was 30 and is now 31, with a limit of 25
- **THEN** the check fails, naming the function, 30, 31 and the limit

#### Scenario: An old complex function edited
- **WHEN** a pull request changes a line inside a function whose complexity is 30 before and after, with a limit of 25
- **THEN** the complexity gate passes

#### Scenario: An excluded file
- **WHEN** the only complex function a change adds is in a path the config excludes
- **THEN** the complexity gate passes

### Requirement: The diff gates compare with a named base
The complexity and audit gates SHALL judge the work against a base revision: the one CI names for the pull request,
merge group or push it tests, or, in a local check, where the work branched from `main`. Local work includes staged
and unstaged changes. When the base can't be found, the check SHALL fail, saying how to fetch it, rather than skip
the gates.

#### Scenario: A local check with no main
- **WHEN** `scripts/check.py` runs in a clone with no `origin/main`
- **THEN** the check fails, saying the complexity gate needs `origin/main` and to run `git fetch origin main`

### Requirement: A changed lock file can't bring in a fixable high-severity advisory
On its audit leg, when the work changes a lock file the config names, a repository's check SHALL audit every dependency
that lock file pins, and SHALL fail on any advisory whose severity is one the config blocks on and that a newer version
fixes. An advisory whose severity can't be found SHALL count as blocking. When the advisory databases can't be reached,
the check SHALL fail saying so, never pass. When no named lock file changed, the audit SHALL NOT run.

#### Scenario: A lock file with a fixable high advisory
- **WHEN** a pull request changes `uv.lock` and a pinned package has a high-severity advisory with a fixed version
- **THEN** the audit leg fails, naming the package, its version, the advisory, its severity and the fixed version

#### Scenario: An advisory with no fix
- **WHEN** a pull request changes a lock file whose only advisory is high-severity with no fixed version
- **THEN** the audit gate passes, and the advisory appears in the weekly report

#### Scenario: No lock file changed
- **WHEN** a pull request changes no lock file the config names
- **THEN** the audit gate passes without auditing, and says so

#### Scenario: The database can't be reached
- **WHEN** the audit leg runs on a changed lock file and the advisory database doesn't answer
- **THEN** the audit leg fails, saying which service it couldn't reach

### Requirement: Only the vulnerable package's own patched release is a fix
For the audit gate and the weekly report, an advisory has a fix only when a patched release of the vulnerable package
itself exists. A change to another package, such as a downgrade of one that depends on it, SHALL NOT count as a fix,
whatever a tool proposes (#330). The patched release SHALL come from the advisory's record; only when that record
can't be had SHALL a tool's own fix count, and only when it names the vulnerable package itself.

#### Scenario: npm offers a downgrade of a dependent as the fix
- **WHEN** a pull request changes `package-lock.json`, a pinned package has a high-severity advisory with no patched
  version, and `npm audit` marks it fixable by downgrading a package that depends on it
- **THEN** the audit gate passes, and the advisory appears in the weekly report, once

#### Scenario: OSV has no record, and npm's fix names the vulnerable package
- **WHEN** a pull request changes `package-lock.json`, OSV has no record of a high-severity advisory (or npm's link
  for it isn't a GitHub advisory id), and `npm audit` fixes it with a newer release of the vulnerable package itself
- **THEN** the audit leg fails, naming that release as the fix (owner, 2026-11-18)

#### Scenario: OSV has no record, and npm's fix names a dependent
- **WHEN** OSV has no record of a high-severity advisory, and `npm audit`'s only fix moves a package that depends on
  the vulnerable one
- **THEN** the audit gate passes, and the advisory appears in the weekly report

### Requirement: Advisories no gate blocks on are reported weekly
Each governed repository SHALL audit all of its lock files once a week on `main`, and SHALL keep one open issue that
lists every advisory found (any severity, with or without a fix), opened when there are advisories, updated in place
while there are, and closed when there are none. It SHALL never open a second one. The issue SHALL be on the troupe
roadmap board.

#### Scenario: Advisories found
- **WHEN** the weekly audit finds advisories and no report issue is open
- **THEN** it opens one listing each advisory's package, version, severity and fixed version, and adds it to the board

#### Scenario: Still there next week
- **WHEN** the weekly audit finds advisories and the report issue is open
- **THEN** it updates that issue's list, and opens no other

#### Scenario: All clear
- **WHEN** the weekly audit finds no advisories and the report issue is open
- **THEN** it closes the issue with a comment saying the audit found none
