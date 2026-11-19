# quality-gates Specification

## Purpose
The merge gates every governed repository's check runs beyond its linters and tests: branch coverage that can't fall,
complexity that can't grow past a limit, and dependencies with no fixable high-severity advisory. Their thresholds
live in one config file per repository, and a weekly report covers the advisories no gate blocks on.

## Requirements

### Requirement: Every threshold lives in the repository's gate config
Each governed repository SHALL declare its gates' thresholds, and any coverage packages and their baselines, in one
file, `quality-gates.toml` at its root, and in no other place. The file SHALL be read strictly: an unknown table or
key, a value of the wrong type, a threshold out of range, or a package whose paths overlap another's SHALL fail the
check, naming the file, the key and what's valid. A missing file SHALL fail the check too: a gate is never skipped
because its config is absent.

#### Scenario: A misspelt key
- **WHEN** `quality-gates.toml` sets `[complexity] block_abve = 25`
- **THEN** the check fails, naming `complexity.block_abve` as unknown and listing the keys `[complexity]` takes

#### Scenario: No config
- **WHEN** a governed repository's check runs and `quality-gates.toml` doesn't exist
- **THEN** the check fails, saying the file is missing and what it must declare

### Requirement: Coverage is declared only where it's measured
`[coverage]` SHALL be the one optional table in `quality-gates.toml`. A repository that infrastructure's list doesn't
name for coverage and mutation testing (spec: mutation-testing) SHALL leave it out, and its coverage leg SHALL then
measure and judge no coverage, and say so.

#### Scenario: No coverage table
- **WHEN** a repository's `quality-gates.toml` has no `[coverage]` table and its coverage leg runs
- **THEN** no coverage is measured or judged, the leg says coverage isn't measured in this repository, and its other
  gates run as usual

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

### Requirement: Delivered files are measured only at their source
The coverage, complexity and size gates SHALL leave out every file the repository's delivered list
(`.github/guard-delivery.json`) names, so a receiving repository declares no pattern of its own for them. Coverage
SHALL drop them before mapping files to packages. A missing list SHALL mean nothing is delivered. A list that can't
be read as a JSON object whose `files` is a list of paths SHALL fail the gate, naming the file and what's wrong.

#### Scenario: A newly delivered script in troupe
- **WHEN** troupe's coverage report includes `scripts/mutation_run.py`, which troupe's delivered list names, with none
  of its statements covered, and troupe's `scripts` package is otherwise at its baseline
- **THEN** the coverage gate passes, and the `scripts` package's measurement doesn't count `scripts/mutation_run.py`

#### Scenario: A delivered file under no package
- **WHEN** a delivered file is in the coverage report and under no declared package
- **THEN** the coverage gate doesn't name it as in no package

#### Scenario: A complex function in a delivered file
- **WHEN** the work changes a delivered file, adding a function above the complexity limit, and the config's
  `exclude` doesn't name the file
- **THEN** the complexity gate passes

#### Scenario: The source repository
- **WHEN** infrastructure, which has no delivered list, runs its gates
- **THEN** every file is measured as its config says, including the files it delivers

#### Scenario: A malformed list
- **WHEN** `.github/guard-delivery.json` isn't valid JSON, or its `files` isn't a list of strings
- **THEN** the gate fails, naming `.github/guard-delivery.json` and the problem, rather than measuring delivered files
  or treating the list as empty

### Requirement: A change can't add or grow a file above the size limit
Every run of a repository's check, local or in CI, SHALL measure the size in bytes of each file the work adds or
changes, against the same base as the complexity gate. It SHALL fail when such a file is above the limit its config
declares (its own ceiling, if the exception list names it, otherwise `[size] block_above`) and is new or larger than
at the base. The failure SHALL name the file, its size before and after, the limit, and the fix.

#### Scenario: A file grows past the limit
- **WHEN** a pull request takes a test file from 45,000 to 52,000 bytes, with `block_above = 49152`
- **THEN** the check fails, naming the file, 45,000, 52,000, the limit, and saying to split the file or declare it in
  `[size.allow]`

#### Scenario: A file already above the limit shrinks
- **WHEN** a pull request edits a file from 60,000 to 59,000 bytes, with `block_above = 49152` and no allowance
- **THEN** the size gate passes

#### Scenario: A declared file within its ceiling
- **WHEN** `[size.allow]` sets `"docs/development-workflow.md" = 90112` and a pull request grows it from 73,297 to
  75,000 bytes
- **THEN** the size gate passes

#### Scenario: A declared file past its ceiling
- **WHEN** a pull request grows a file `[size.allow]` caps at 90,112 bytes to 90,200
- **THEN** the check fails, naming the file, its sizes, its ceiling and the fix

### Requirement: Large files are noted before they block
The size gate SHALL print each file the work adds or changes that is above `[size] warn_above` and within its limit,
with its size, without failing.

#### Scenario: A file over one Read
- **WHEN** a pull request grows a file to 40,000 bytes, with `warn_above = 32768` and `block_above = 49152`
- **THEN** the size gate passes and prints the file, 40,000 and the warning threshold

### Requirement: Some files are never measured for size
The size gate SHALL NOT measure binary files (any file containing a NUL byte or not valid UTF-8), delivered files, or
paths the config's `[size] exclude` globs match.

#### Scenario: A fixture over the limit
- **WHEN** `[size] exclude` holds `**/fixtures/**` and a pull request adds a 256,000-byte fixture under
  `scripts/tests/fixtures/`
- **THEN** the size gate passes

#### Scenario: A binary file
- **WHEN** a pull request adds a 100,000-byte PNG
- **THEN** the size gate passes

### Requirement: The size exception list can only shrink
Each `[size.allow]` entry SHALL name a file and its ceiling in bytes, above `block_above`. The check SHALL fail when
an entry names a file that doesn't exist, or that is at or under `block_above`, saying to remove the entry.

#### Scenario: A declared file is split
- **WHEN** a pull request splits a file `[size.allow]` names, leaving it at 30,000 bytes, with `block_above = 49152`
- **THEN** the check fails, naming the entry and saying to remove it from `[size.allow]`

#### Scenario: A ceiling at or below the limit
- **WHEN** `[size.allow]` gives a file a ceiling of 45,000 with `block_above = 49152`
- **THEN** the check fails, naming the entry and saying a ceiling must be above `block_above`

### Requirement: A repository declares the size gate's limits in its gate config
`quality-gates.toml` SHALL declare the size gate in a `[size]` table, with `block_above` and `warn_above` in bytes
(`warn_above` at or below `block_above`), and optionally `exclude` and `[size.allow]`. Until every governed repository
declares it, `[size]` SHALL be optional: without it, the size gate measures nothing and says the size gate isn't
declared in this repository, and the other gates run as usual.

#### Scenario: No size table
- **WHEN** a repository's `quality-gates.toml` has no `[size]` table and its check runs
- **THEN** the size gate measures nothing and says it isn't declared in this repository, and the other gates run

#### Scenario: Warning above the limit
- **WHEN** `[size]` sets `warn_above = 50000` and `block_above = 49152`
- **THEN** the check fails, naming `size.warn_above` and saying it must be at or below `block_above`
