## ADDED Requirements

### Requirement: Source and test files are split into parts, each read by its own session
Before any session starts, a review run SHALL split the changed source and test files into parts of at most a declared
number of Reads, keeping each file's targets in one part and files of one folder together, up to a declared number of
parts. Each part SHALL be reviewed by its own session. The first part SHALL also carry the prose and the
whole-pull-request checks. A pull request whose source and test files fit in one part SHALL get one session.

#### Scenario: A small pull request
- **WHEN** a pull request changes three Python files and a Markdown file, needing 8 Reads
- **THEN** one session reviews it, reading the three files and the Markdown file, and doing every check

#### Scenario: A runner pull request
- **WHEN** a pull request's source and test files need three times the declared Reads per part
- **THEN** three sessions run, each with its own list, and together the lists hold every source and test file once

#### Scenario: More than the parts allow
- **WHEN** a pull request's source and test files need more Reads than the declared parts times the Reads per part
- **THEN** the declared number of sessions runs, each part larger than the declared Reads, and no file is left off

#### Scenario: Nothing but prose and data
- **WHEN** a pull request changes only Markdown, files under `openspec/` and fixtures
- **THEN** one session reviews it, with the prose to read and no source or test file

#### Scenario: A newer push
- **WHEN** a member pushes while a review's parts are running
- **THEN** every session of the earlier review that shares a part number with the new review is cancelled

### Requirement: Source and test files left unread are read by a follow-up session
After the parts' sessions finish, the run SHALL measure what they read together. If any changed source or test file
wasn't read in full, the run SHALL start a round of follow-up sessions, split as the parts are, over only those
files, each told that an earlier session left them unread. It SHALL do so again after that round, and SHALL start
no more than two follow-up rounds.

#### Scenario: A session that stopped early
- **WHEN** a review's only session reads 7 of 39 files in full and none of its 16 source and test files, then ends
  by itself, as on troupe#325
- **THEN** a follow-up session starts over the 16 source and test files, and the check judges what both read

#### Scenario: Every source and test file read
- **WHEN** the parts' sessions read every source and test file in full
- **THEN** no follow-up session starts

#### Scenario: Prose left unread
- **WHEN** the parts' sessions read every source and test file but left a Markdown file unread
- **THEN** no follow-up session starts, and the check warns, naming the Markdown file

#### Scenario: The first follow-up stops early too
- **WHEN** the first follow-up session leaves two source files unread
- **THEN** a second follow-up session starts over those two files

#### Scenario: The second follow-up stops early too
- **WHEN** the second follow-up session leaves a source file unread
- **THEN** no third follow-up round starts, and `claude review completed` fails, naming that file

### Requirement: A review's sessions report as one review
Each session SHALL post its findings as inline comments, and SHALL give back a summary of its part in its structured
output, never as a comment of its own. After every session, the resolving job SHALL post one top-level comment that
holds every session's summary and the measured coverage. Claude's tools SHALL NOT include posting a top-level comment.

#### Scenario: Three parts
- **WHEN** a review runs three sessions and a follow-up session
- **THEN** the pull request gets one top-level comment from the review App, with each session's summary and what was
  read, and each finding as its own inline conversation

#### Scenario: A session's summary is missing
- **WHEN** one session's structured output has no summary
- **THEN** the comment says that part's summary is missing, and the check still judges coverage from its tool calls

#### Scenario: The tools are widened
- **WHEN** a change gives Claude `gh pr comment` again, or a tool that posts a top-level comment
- **THEN** `scripts/check.py` fails, naming the tool

### Requirement: A session resolves or re-tiers only the conversations of its part
A session's request to resolve or re-tier a conversation SHALL be carried out only when the conversation is on a file
in that session's list. Conversations on a file in no session's list, or on no file, SHALL be the first part's. The
check SHALL be made against the conversations read before the sessions started, never against what Claude says.

#### Scenario: A finding on another part's file
- **WHEN** the second part's session names a must-fix on a file in the first part's list
- **THEN** the resolving job leaves it open, and names it in the run's log as outside that session's part

#### Scenario: A finding on prose
- **WHEN** the first part's session names a nit on `README.md`, whose problem a push fixed
- **THEN** the resolving job resolves it

### Requirement: The check fails unless every changed source and test file was read in full
`claude review completed` SHALL fail when a changed source or test file wasn't read in full by any of the review's
sessions, naming each one, or when coverage is unknown, missing or malformed. Prose left unread SHALL NOT fail it: the
check SHALL pass with one warning naming each. Data files SHALL be named as left to their tests. A failure SHALL say
how to get a review that reads the code.

#### Scenario: troupe#325's runs
- **WHEN** the sessions together read 10 of 16 changed source and test files in full
- **THEN** `claude review completed` fails, naming the 6 files

#### Scenario: A review that read no code
- **WHEN** a review's sessions read only the task list and the Markdown files
- **THEN** `claude review completed` fails, naming every changed source and test file

#### Scenario: Every source and test file read, prose skipped
- **WHEN** the sessions read every source and test file in full and left two Markdown files unread
- **THEN** `claude review completed` passes, with one warning naming the two Markdown files

#### Scenario: Data left to its tests
- **WHEN** a pull request adds 40 fixture files that tests name, and the sessions read every source and test file
- **THEN** `claude review completed` passes, and the run's summary lists the 40 files as data left to its tests

#### Scenario: No source or test file changed
- **WHEN** a pull request changes only Markdown and files under `openspec/`
- **THEN** `claude review completed` passes once the review completes, with a warning naming any file not read

#### Scenario: Coverage unknown
- **WHEN** a session's record of its tool calls can't be read, or a part's coverage record is missing
- **THEN** `claude review completed` fails, saying coverage couldn't be measured, and naming the part

#### Scenario: The lead session failed
- **WHEN** a pull request changes only Markdown, and its one session fails, for example because the Claude token
  expired, so its action step fails without failing its job
- **THEN** `claude review completed` fails, saying coverage couldn't be measured and naming round 1 part 1

#### Scenario: The check is weakened
- **WHEN** a change lets the check pass with a source or test file unread, drops a part's record from the union, or
  reads Claude's structured output or summary to decide coverage
- **THEN** `scripts/check.py` fails, naming what changed

### Requirement: Data that nothing names is read as source and test
A file the list makes data SHALL stay data only when a tracked file that isn't data, outside the change's own
`openspec/` folder, names the data file's name or the name of the folder that holds it. Otherwise the plan step SHALL
count it as source and test, so it must be read in full. The run's summary SHALL say why.

#### Scenario: A fixture its test loads
- **WHEN** a pull request adds `fixtures/responses/refusal/replies.json`, and a test names `replies.json`
- **THEN** it's data, left to its tests

#### Scenario: A stray data file
- **WHEN** a pull request adds `notes/old-export.json`, and no tracked file that isn't data names `old-export.json`
  or `notes`
- **THEN** it counts as source and test, and the run's summary says nothing names it

#### Scenario: Named only by other data
- **WHEN** a JSON file's name appears only in another JSON file and in the change's proposal
- **THEN** it counts as source and test

## MODIFIED Requirements

### Requirement: The review reads everything listed, and the uses of what changed
The prompt SHALL tell each session to read everything on its own list in full with Read before it gives its summary,
and SHALL say that a review that hasn't is not a clean one. It SHALL tell the session to search for the uses of each
changed or removed name and read them. The session's summary SHALL say what it read, and name each file on its list
it didn't read in full. Claude's tools SHALL NOT grow.

#### Scenario: The prompt
- **WHEN** this repository's tests read the review's prompt
- **THEN** they fail if it doesn't name the session's list, doesn't tell the session to read everything on it,
  doesn't ask for the uses of changed names to be read, or doesn't ask the summary to name each file on the list not
  read in full

#### Scenario: A part's prompt
- **WHEN** the second of three parts' sessions starts
- **THEN** its prompt names its own list, says other sessions read the rest, and doesn't ask it to do the
  whole-pull-request checks

#### Scenario: A follow-up's prompt
- **WHEN** a follow-up session starts
- **THEN** its prompt names only the files left unread, and says an earlier session didn't read them

### Requirement: The review's coverage is measured from its tool calls
After each session, a step SHALL work out what the session read, from the action's record of its tool calls, never
from anything Claude wrote. A listed file SHALL count as read in full only when Read calls that succeeded, in one or
more of the review's sessions, together cover every line of everything listed for it. It SHALL count as read in part
when they cover some, and as not read otherwise. The run's summary SHALL list each file's coverage.

#### Scenario: Everything read
- **WHEN** the session's Read calls cover every line of every listed file and diff
- **THEN** the run's summary lists every file as read in full

#### Scenario: Part of a file read
- **WHEN** an added file is 3,000 lines and the session read lines 1 to 2,000 of it
- **THEN** the run's summary lists that file as read in part

#### Scenario: The diff read, but not the file
- **WHEN** the session read a modified file's whole diff but none of the file itself
- **THEN** the run's summary lists that file as read in part

#### Scenario: A file read across two sessions
- **WHEN** a part's session read a modified file's diff, and the follow-up session read the file itself
- **THEN** the run's summary lists that file as read in full

#### Scenario: The summary claims more than was read
- **WHEN** Claude's summary says it read every file, but the session made no Read call on one of them
- **THEN** that file is listed as not read

#### Scenario: A Read that failed
- **WHEN** a Read call on a listed file returned an error
- **THEN** it counts for nothing

#### Scenario: The record can't be read
- **WHEN** the action left no record of the session's tool calls, or one that can't be parsed
- **THEN** every file on that session's list counts as not read by it, and the review's coverage is unknown

### Requirement: The review's turn budget scales with the reading needed
Each session's turn limit SHALL be a base plus an amount for each Read call its own list needs, at the Read tool's
measured size per call, up to a declared cap. The review jobs' timeout SHALL be long enough for the cap. A session
that runs out of turns or time SHALL leave its unread source and test files to the follow-up rounds, and SHALL fail
`claude review completed` if they're still unread after it.

#### Scenario: A small pull request
- **WHEN** a pull request lists one modified 300-line file
- **THEN** the session's turn limit is the base plus two Reads' worth: the file and its diff

#### Scenario: A part
- **WHEN** a part's list needs 40 Reads, and the whole pull request needs 130
- **THEN** that session's turn limit is the base plus 40 Reads' worth

#### Scenario: A pull request past the cap
- **WHEN** a part's list needs more Reads than the cap allows turns for, and its session doesn't read them all
- **THEN** the follow-up rounds take the source and test files it left, and `claude review completed` fails, naming
  any still unread after them

#### Scenario: A session that runs out of turns
- **WHEN** a part's session runs out of turns with two source files unread
- **THEN** the follow-up session reads them, and the check passes if it does

### Requirement: One declared list decides which changed files are source and test
Before any session starts, the plan step SHALL sort each listed file with a line to read into source and test, prose
or data, from one declared list. Prose is Markdown, plain text, SVG, licence files and anything under `openspec/`.
Data is JSON, recorded streams and tables, and files with no suffix in a `fixtures/` folder, except declared
configuration. Every other file counts as source and test, kinds the list doesn't name included. The run's summary SHALL show each file's kind.

#### Scenario: A module and its tests
- **WHEN** a pull request changes `src/troupe_runner_ollama/conversation.py` and `tests/test_ollama_conversation.py`
- **THEN** both count as source and test

#### Scenario: Fixtures and recorded streams
- **WHEN** a pull request changes `fixtures/ollama/thinking/events.json`, a `.jsonl` recording elsewhere, and
  `fixtures/claude/stream-error`, a recorded stream with no suffix, and test code names each of them or its folder
- **THEN** each is data

#### Scenario: JSON that configures something
- **WHEN** a pull request changes `package.json`, `tsconfig.base.json`, `tofu/required-checks.json` and
  `.github/dependabot.json`
- **THEN** each counts as source and test

#### Scenario: Code in a fixtures folder
- **WHEN** a pull request changes `tests/fixtures/conftest.py`
- **THEN** it counts as source and test

#### Scenario: Prose and licences
- **WHEN** a pull request changes `README.md`, `contributing/runners.md`, `LICENSE` and
  `openspec/changes/x/.openspec.yaml`
- **THEN** each is prose

#### Scenario: A workflow or a kind the list doesn't name
- **WHEN** a pull request changes `.github/workflows/ci.yml` or a `.astro` page
- **THEN** each counts as source and test

#### Scenario: An empty file
- **WHEN** a pull request adds an empty `__init__.py`, which has no line to read
- **THEN** it has no kind, so reading it doesn't count towards the check

#### Scenario: Skip-listed and binary files
- **WHEN** a pull request changes `uv.lock` and a PNG
- **THEN** neither has a kind, since neither needs anything read

#### Scenario: The run's summary
- **WHEN** a review run finishes
- **THEN** its summary's table says, for each file, its kind and how it was read, and how many source and test files
  were read in full

#### Scenario: The list is changed
- **WHEN** a change edits the declared list, or the step's script, without moving the test's pin
- **THEN** `scripts/check.py` fails, naming the step whose script isn't the one pinned

## REMOVED Requirements

### Requirement: The check fails a review that read none of the changed code
**Reason**: Decision #278 and #279: data is left to its tests, and the reading that's left is split across sessions,
so the check can again need every changed source and test file read. That's stronger than #282's floor, so the floor
still holds.
**Migration**: "The check fails unless every changed source and test file was read in full" replaces it. A review
that read no code still fails, and so does one that read only part of the code.
