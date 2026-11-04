# Spec Delta

## ADDED Requirements

### Requirement: The changed files and their diffs are listed before the review starts
Before Claude starts, a review run SHALL write each changed file's diff into the workspace, made from the checked-out
commit, and a list of what must be read: an added file whole; a modified or renamed file whole, as it is now, and its
diff; a deleted file's diff. A path the review's action restores from the base SHALL be read as its copy of the pull
request's version. Each target SHALL list the Reads that cover it. Binary files and a declared skip list need nothing.

#### Scenario: A large pull request
- **WHEN** a pull request adds 9,000 lines across 114 files
- **THEN** each of its changed text files has its whole diff in the workspace, none cut short, and the list names
  each file and diff to read

#### Scenario: A modified file
- **WHEN** a pull request changes one function in a 600-line module
- **THEN** the list names the whole module and its diff

#### Scenario: A pull request that grows CLAUDE.md
- **WHEN** a pull request adds two lines to `CLAUDE.md`, which the action puts back from the base before Claude starts
- **THEN** the list names the action's copy of the pull request's `CLAUDE.md` and counts the pull request's lines

#### Scenario: A long file
- **WHEN** a pull request adds a 60 KB file
- **THEN** its target lists consecutive Reads that cover every line, each small enough that Read returns it whole

#### Scenario: A deleted file
- **WHEN** a pull request deletes a module
- **THEN** the list names its diff, which holds every line that was removed

#### Scenario: A lockfile
- **WHEN** a pull request changes `uv.lock`
- **THEN** the list needs nothing read for it, and says it's on the skip list

#### Scenario: Attributes that mark code binary
- **WHEN** a pull request adds a `.gitattributes` with `*.py -diff` and changes a `.py` file
- **THEN** that file's targets are listed as for any text file

#### Scenario: The diff can't be made
- **WHEN** the diff can't be made from the checkout
- **THEN** the run fails before Claude starts, saying so

### Requirement: The review reads everything listed, and the uses of what changed
The prompt SHALL tell the review to read everything on the list in full with Read before it posts its summary, and
SHALL say that a review that hasn't is not a clean one. It SHALL tell the review to search for the uses of each
changed or removed name and read them. The summary SHALL say what it read. Claude's tools SHALL NOT grow.

#### Scenario: The prompt
- **WHEN** this repository's tests read the review's prompt
- **THEN** they fail if it doesn't name the list, doesn't tell the review to read everything on it, or doesn't ask
  for the uses of changed names to be read

### Requirement: The review's coverage is measured from its tool calls
After the review, a step SHALL work out what the session read, from the action's record of its tool calls, never
from anything Claude wrote. A listed file SHALL count as read in full only when Read calls that succeeded cover every
line of everything listed for it, as read in part when they cover some, and as not read otherwise. The run's summary
SHALL list each file's coverage.

#### Scenario: Everything read
- **WHEN** the session's Read calls cover every line of every listed file and diff
- **THEN** the run's summary lists every file as read in full

#### Scenario: Part of a file read
- **WHEN** an added file is 3,000 lines and the session read lines 1 to 2,000 of it
- **THEN** the run's summary lists that file as read in part

#### Scenario: The diff read, but not the file
- **WHEN** the session read a modified file's whole diff but none of the file itself
- **THEN** the run's summary lists that file as read in part

#### Scenario: The summary claims more than was read
- **WHEN** Claude's summary says it read every file, but the session made no Read call on one of them
- **THEN** that file is listed as not read

#### Scenario: A Read that failed
- **WHEN** a Read call on a listed file returned an error
- **THEN** it counts for nothing

#### Scenario: The record can't be read
- **WHEN** the action left no record of the session's tool calls, or one that can't be parsed
- **THEN** every listed file counts as not read

### Requirement: Call sites are reported, not gated
The run's summary SHALL also list, from the same record, the searches the session made and the files it read that
weren't changed, so a reader can see whether it looked at the uses of what changed. Whether it did SHALL NOT change
whether `claude review completed` passes.

#### Scenario: A review that looked at callers
- **WHEN** the session searched for a changed function's name and read two unchanged files that call it
- **THEN** the run's summary lists the search and the two files

#### Scenario: A review that didn't
- **WHEN** the session read everything listed but searched for nothing
- **THEN** the run's summary says it made no search and read no unchanged file, and the check doesn't fail for that

### Requirement: The check fails a review that didn't read everything listed
`claude review completed` SHALL fail when the review of the head didn't read every listed file in full, even if the
review and its resolving job succeeded. Its message SHALL name each file read in part or not at all, and say how to
get a review that reads them: re-run the run, make the pull request smaller, or have the owner review it by hand and
bypass the rules.

#### Scenario: A review that skimmed
- **WHEN** a review succeeds, posts a clean summary saying the implementation wasn't checked, and made no Read call
  on most of the listed files
- **THEN** `claude review completed` fails, naming those files, and the pull request can't merge

#### Scenario: A review that read everything
- **WHEN** a review and its resolving job succeed, and every listed file was read in full
- **THEN** `claude review completed` passes

#### Scenario: Nothing to read
- **WHEN** a pull request changes only files that need nothing read, such as a lockfile
- **THEN** `claude review completed` doesn't fail for coverage

#### Scenario: The coverage step is dropped or weakened
- **WHEN** a change removes the coverage step, lets the check pass without its result, or makes it read Claude's
  structured output or summary
- **THEN** `scripts/check.py` fails, naming what changed

### Requirement: The review's turn budget scales with the reading needed
The review's turn limit SHALL be a base plus an amount for each Read call the listed files and diffs need, at the
Read tool's measured size per call, up to a declared cap. The review job's timeout SHALL be long enough for the
cap. A review that runs out of turns or time SHALL fail `claude review completed`, through its failure or its
coverage.

#### Scenario: A small pull request
- **WHEN** a pull request lists one modified 300-line file
- **THEN** the review's turn limit is the base plus two Reads' worth: the file and its diff

#### Scenario: A pull request past the cap
- **WHEN** a pull request needs more Reads than the cap allows turns for, and the review doesn't read them all
- **THEN** `claude review completed` fails, naming the files not read, and the pull request can't merge until a
  review reads them or the owner bypasses the rules

### Requirement: The review's model is a declared variable
The review SHALL run on the model named by the Actions variable `CLAUDE_REVIEW_MODEL`. OpenTofu SHALL set it on
troupe, infrastructure and website from one declared value. A run where it's unset, or isn't a Claude model name,
SHALL fail before Claude starts, naming the variable.

#### Scenario: The model is changed
- **WHEN** the declared value is changed and the plan applied
- **THEN** the next review in each of the three repositories runs on the new model, with no change to the workflow

#### Scenario: The variable is unset
- **WHEN** a review runs in a repository without `CLAUDE_REVIEW_MODEL`
- **THEN** the review fails before Claude starts, naming the variable, and `claude review completed` fails

#### Scenario: The variable holds something else
- **WHEN** `CLAUDE_REVIEW_MODEL` holds a value with a space or a `--` flag
- **THEN** the review fails before Claude starts, naming the variable, and the value never reaches Claude's arguments
