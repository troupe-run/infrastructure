# Proposal

## Why

Claude's review can't pass a large pull request honestly. On troupe-run/troupe#325 (39 files) `claude review
completed` failed the coverage floor three times. Each time the review read none of the 16 changed source and test
files in full, posted no findings, and the owner merged with a bypass. troupe#297 (126 files) failed on coverage
twice. Decision #278 (owner, 2026-11-06) settles the fix: data is validated by the code and tests that use it, so the
review doesn't read it in full, and whatever is left that one session doesn't read gets split across sessions. The LM
Studio runner's pull request (troupe#379) is next, and it will look like #297, so this is time-sensitive.

**What the runs show (#279 asked for this first).** No session ran out of turns. Every one ended by itself, with
`subtype: success`:

| Pull request, run | Reads planned | Turn limit | Turns used | Read in full |
|---|---|---|---|---|
| troupe#325, 43017411898, attempts 1 to 3 | 85 | 210 | 33, 13, 47 | 1, 1, 7 of 39 files; 0 of 16 source and test |
| troupe#297, 42169746660 | 130 | 300 | 65 | 39 of 105 |
| troupe#297, 42171054622, attempts 1 and 2 | 133 | 306 | 37, 30 | 21, 12 of 107 |
| troupe#297, 42212920393 | 151 | 342 | 25 | 13 of 113 |
| troupe#297, 42173858575 (passed) | 133 | 306 | 145 | 106 of 106 |
| troupe#297, 42212004025 (passed) | 151 | 342 | 164 | 113 of 113 |

A session that commits to the list reads 150 Reads in one go. A session that doesn't stops after a minute, whatever
the size. So most failures come from a session stopping early, not from a pull request too big for one session.
#325 was well within one session's budget. Splitting by size alone would have left #325 as it was. A session that
stops early has to be followed by another session over what it left unread.

## What Changes

- **Data is off the must-read list.** Before the review starts, the plan step sorts each changed file with text to
  read into one of three kinds, from one declared list:
  - **source and test**: must be read in full, and the check enforces it.
  - **prose**: Markdown, text, `openspec/`, licence files. The review is asked to read it and the check warns, as now.
  - **data**: JSON and recorded streams (`.json`, `.jsonl`, `.ndjson`, `.csv`, `.tsv`), and files with no suffix in a
    `fixtures/` directory. It's listed for the review to see, not required, and left to the tests that use it.
- **Data that nothing names is read.** A data file counts as data only when some tracked file that isn't data names
  its file name or its folder. Otherwise it goes on the must-read list as source and test, so a stray data file is read
  rather than waved through.
- **The reading is split into parts.** The source and test files are split into parts of at most a declared number of
  Reads, each read by its own session, in parallel. The first part also does the whole-pull-request checks (OpenSpec
  tasks, the issue, commits, `CLAUDE.md`, the org guide) and reads the prose. A small pull request is one part, as
  today.
- **Follow-up sessions read what was left.** After the parts finish, the run measures what they read together. If
  any source or test file isn't read in full, a round of follow-up sessions takes only those files, and a second
  round takes whatever the first left (owner, 2026-11-11: two rounds). That's how a session
  that stopped early gets caught up, which is #325's case.
- **One review.** Each session posts its findings inline, as now, and gives back a summary of its part. The resolving
  job posts one top-level comment that combines them, with the measured coverage. Sessions no longer post their own
  summary. `Bash(gh pr comment:*)` comes off Claude's tools, so Claude has fewer tools than before. A session may
  name a conversation to resolve or re-tier only if the conversation is on a file in its part. The first part also
  handles conversations on files outside every part.
- **The check reads every changed source and test file.** `claude review completed` passes only when the sessions
  together read every source and test file in full, and fails when coverage is unknown. Unread prose stays a warning,
  and data is listed as left to its tests. #282's floor stays: a review that read no code still fails, and now so does
  one that read only part of it.
- `docs/development-workflow.md` ("Claude's review"), `CLAUDE.md`, `README.md` and `org-profile/CONTRIBUTING.md` say
  what a passing review means after this.

Out of scope:
- Carrying coverage forward across a pull request's runs, which is #280. Until #280 lands, each run reads all the
  code again, with parts and follow-up sessions doing the reading.
- A size limit on pull requests (#278, option C, not chosen).
- File-size limits (#271).
- The review's model.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pr-review`:
  - The plan sorts files into source and test, prose and data, and splits the source and test files into parts.
  - Sessions run per part, and follow-up sessions read what's still unread.
  - Coverage is the union of every session's reads.
  - The check needs every source and test file read.
  - One combined summary is posted by the resolving job.
  - Each session gets a turn budget for its own part.
  - A session's resolves are limited to its own part.
- `development-workflow`: the workflow docs say what a passing review means now, and what to do when it fails.

## Impact

- `.github/workflows/claude-review.yml` changes most:
  - A new plan job: the diff, the kinds of file, and the parts.
  - The review job runs as a matrix of parts.
  - Two follow-up jobs, also matrices, read what's still unread, each after a planning job.
  - The resolving job also posts the summary.
  - `completed` judges the union of coverage records.
  - Records pass between jobs as artifacts of the same run.
- The workflow is delivered to troupe and website. The merge's plan shows those deliveries, and
  `org-profile/CONTRIBUTING.md`'s delivery to troupe-run/.github.
- `scripts/tests/test_claude_review_workflow.py`: the jobs' structure, new hash pins, and behaviour tests that run the
  plan, merge and check scripts against troupe#325's and #297's shapes.
- A large pull request costs more: several sessions, plus up to two follow-up rounds when a session stops early. Each session
  starts by reading `CLAUDE.md`, the pull request and the conversations again.
- No new secret, App permission or dependency. Claude has one tool fewer.
