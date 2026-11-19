## ADDED Requirements

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
