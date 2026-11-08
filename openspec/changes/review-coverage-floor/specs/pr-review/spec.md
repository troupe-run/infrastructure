## RENAMED Requirements

- FROM: `### Requirement: The check fails a review that didn't read everything listed`
- TO: `### Requirement: The check fails a review that read none of the changed code`

## MODIFIED Requirements

### Requirement: The check fails a review that read none of the changed code
Until #280 makes coverage blocking again, `claude review completed` SHALL fail when the review succeeded but read none
of the changed source and test files in full, naming them, or when its coverage is unknown, missing or malformed. Any
other coverage short of complete SHALL NOT fail it. The check SHALL then pass with one warning that names each file
not read in full. A failure SHALL say how to get a review that reads the code: re-run, a smaller pull request, or the
owner's bypass.

#### Scenario: A review that skimmed
- **WHEN** a review succeeds, posts a clean summary saying the implementation wasn't checked, and read only the task
  list, none of the changed source or test files
- **THEN** `claude review completed` fails, naming those source and test files, and the pull request can't merge

#### Scenario: A review that read part of every code file
- **WHEN** a review succeeds and read some lines of each changed source and test file, but none of them in full
- **THEN** `claude review completed` fails, naming them

#### Scenario: A review that read everything
- **WHEN** a review and its resolving job succeed, and every listed file was read in full
- **THEN** `claude review completed` passes, with no warning

#### Scenario: A review that read some of the code
- **WHEN** a review succeeds, read the changed module in full, read four changed test files in part, and didn't read
  ten changed fixture files, as on troupe#318
- **THEN** `claude review completed` passes, with one warning that names the four test files and the ten fixtures

#### Scenario: No source or test file changed
- **WHEN** a pull request changes only Markdown and files under `openspec/`, and the review read none of them in full
- **THEN** `claude review completed` passes, with one warning that names them

#### Scenario: Nothing to read
- **WHEN** a pull request changes only files that need nothing read, such as a lockfile
- **THEN** `claude review completed` passes, with no warning

#### Scenario: Coverage unknown
- **WHEN** the coverage step couldn't read the list of changed files or the session's record
- **THEN** `claude review completed` fails, saying coverage couldn't be measured, so nothing counts as read

#### Scenario: The coverage step's outputs are missing or malformed
- **WHEN** the review succeeded but the coverage step set no coverage, no floor result, or a value it never writes
- **THEN** `claude review completed` fails, saying coverage wasn't measured

#### Scenario: More than fifty files unread
- **WHEN** the check passes with sixty files not read in full
- **THEN** its warning names fifty of them, then says "and 10 more"

#### Scenario: The coverage step is dropped or weakened
- **WHEN** a change removes the coverage step, lets the check pass without its results, makes it read Claude's
  structured output or summary, or lets it pass when no changed source or test file was read in full
- **THEN** `scripts/check.py` fails, naming what changed

### Requirement: The review reads everything listed, and the uses of what changed
The prompt SHALL tell the review to read everything on the list in full with Read before it posts its summary, and
SHALL say that a review that hasn't is not a clean one. It SHALL tell the review to search for the uses of each
changed or removed name and read them. The summary SHALL say what it read, and name each listed file it didn't read
in full. Claude's tools SHALL NOT grow.

#### Scenario: The prompt
- **WHEN** this repository's tests read the review's prompt
- **THEN** they fail if it doesn't name the list, doesn't tell the review to read everything on it, doesn't ask for
  the uses of changed names to be read, or doesn't ask the summary to name each listed file not read in full

### Requirement: The review's turn budget scales with the reading needed
The review's turn limit SHALL be a base plus an amount for each Read call the listed files and diffs need, at the
Read tool's measured size per call, up to a declared cap. The review job's timeout SHALL be long enough for the
cap. A review that runs out of turns or time SHALL fail `claude review completed` through its failure, or through
the check's floor when it read none of the changed source and test files in full. Otherwise the check SHALL warn,
naming the files it didn't read.

#### Scenario: A small pull request
- **WHEN** a pull request lists one modified 300-line file
- **THEN** the review's turn limit is the base plus two Reads' worth: the file and its diff

#### Scenario: A pull request past the cap
- **WHEN** a pull request needs more Reads than the cap allows turns for, and the review doesn't read them all
- **THEN** `claude review completed` names the files not read: it fails if the review job failed or no changed source
  or test file was read in full, and otherwise passes with a warning

## ADDED Requirements

### Requirement: One declared list decides which changed files are source and test
The coverage step SHALL decide which listed files count as source or test for the check's floor from one declared
list of data and prose kinds: Markdown and plain text, JSON and recorded streams, SVG, licence files, anything under
`openspec/`, and anything in a `fixtures/` directory. Every other listed file with at least one line to read SHALL
count, including kinds the list doesn't name. The run's summary SHALL show whether each file counts.

#### Scenario: A module and its tests
- **WHEN** a pull request changes `src/troupe_runner_ollama/conversation.py` and `tests/test_ollama_conversation.py`
- **THEN** both count as source and test

#### Scenario: Fixtures and recorded streams
- **WHEN** a pull request changes `fixtures/ollama/thinking/events.json` and a `.jsonl` recording elsewhere
- **THEN** neither counts

#### Scenario: Prose and licences
- **WHEN** a pull request changes `README.md`, `contributing/runners.md`, `LICENSE` and
  `openspec/changes/x/.openspec.yaml`
- **THEN** none of them counts

#### Scenario: A workflow or a kind the list doesn't name
- **WHEN** a pull request changes `.github/workflows/ci.yml` or a `.astro` page
- **THEN** each counts as source and test

#### Scenario: An empty file
- **WHEN** a pull request adds an empty `__init__.py`, which has no line to read
- **THEN** it doesn't count, so reading it doesn't meet the floor

#### Scenario: Skip-listed and binary files
- **WHEN** a pull request changes `uv.lock` and a PNG
- **THEN** neither counts, since neither needs anything read

#### Scenario: The run's summary
- **WHEN** a review run finishes
- **THEN** its summary's table says, for each file, whether it counts as source and test, and how many of those were
  read in full

#### Scenario: The list is changed
- **WHEN** a change edits the declared list, or the step's script, without moving the test's pin
- **THEN** `scripts/check.py` fails, naming the step whose script isn't the one pinned
