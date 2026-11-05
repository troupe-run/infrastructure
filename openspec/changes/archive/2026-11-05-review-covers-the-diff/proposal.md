# Proposal

## Why

troupe-run/troupe#283 (114 files, about 9,000 added lines) got clean reviews whose summaries said they hadn't read
the code, and `claude review completed` passed each time, so the workflow treated it as reviewed (#268). The issue
guessed that the turn and time limits were the cause. The runs' logs show they weren't: the four reviews of #283 used
9 to 14 of their 30 turns, took 15 to 28 seconds, had no tool call refused, and ran on `claude-sonnet-5-5`, the
action's default. The review stopped early because nothing made it read the diff, and nothing checked whether it had.

## What Changes

- **The review is told what changed and what it must read.** The checkout already holds the whole branch as it would
  merge. Before Claude starts, a step writes the list of changed files and each one's diff under `.review-diff/`,
  made with `git diff` from the merge commit's first parent, so a large pull request's diff isn't cut short the way
  one `gh pr diff` output is. What must be read depends on the file:
  - an added file: the whole file;
  - a modified or renamed file: the whole file as it is now, and its diff, which also shows what was removed;
  - a deleted file: its diff, the only record of what went;
  - a binary file, or one on a declared skip list (lockfiles and OpenTofu state): nothing.
- **The prompt tells the review to read everything listed in full** with Read, and says a review that hasn't isn't a
  clean one. It also asks the review to search for the uses of each changed or removed name, and read them: a change
  that breaks its call sites can't be seen from the changed files alone. Its summary says what it read.
- **A step after the review measures coverage from the session's own tool calls.** It reads the action's execution
  file, which Claude can't reach or write, and doesn't read anything Claude wrote. A listed file counts as read only
  when Read calls that succeeded cover every line of everything listed for it. Its result goes in the run's summary:
  each listed file read in full, in part, or not at all. The summary also reports the review's searches and the
  unchanged files it read, so a reader can see whether it looked at call sites. That part is reported, not enforced.
- **`claude review completed` fails when any listed file wasn't read in full**, and names those files. A re-run, a
  smaller pull request, or the owner's bypass after a review by hand clears it. "Not checked" under a green check
  can no longer happen.
- **The turn budget scales with the reading needed**: a base, plus turns for each Read the listed files need at the
  Read tool's measured size per call, up to a cap. The job's timeout goes from 20 to 90 minutes. A pull request too
  large for the cap fails the check saying so, rather than passing.
- **The review's model is a declared Actions variable**, `CLAUDE_REVIEW_MODEL`, set by OpenTofu on troupe,
  infrastructure and website from one local value, `claude-sonnet-5-5` for now (owner, 2026-11-04). A run where it's
  unset or isn't a model name fails, naming the variable.
- **BREAKING (process):** a pull request whose review didn't read every listed file and diff can't merge until a review does,
  or the owner bypasses the rules. A large pull request's review costs more, on every push.
- `docs/development-workflow.md` ("Claude's review") says what a passing review means and what it doesn't.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pr-review`: new requirements that the review is given the changed files and their diffs and reads them all, that
  its coverage is measured from its tool calls, that call sites are asked for and reported but not gated, that
  `claude review completed` fails a review that didn't read what was listed, that its turn budget scales with the
  reading needed, and that its model is a declared variable.
- `development-workflow`: a new requirement that the workflow doc says what a passing review means and what it
  doesn't.

## Impact

- `.github/workflows/claude-review.yml`: new steps before and after the review, a scaled `--max-turns`, `--model`, a
  longer timeout, the prompt, and the `completed` job. Delivered to troupe and website.
- `scripts/tests/test_claude_review_workflow.py`: pins the new steps and tests their scripts, including a session that
  says "not checked" and doesn't read the diff.
- `tofu/`: a new `review.tf` with the variable on three repositories; the guard delivery waits for it.
- `docs/development-workflow.md`.
- Cost: a review now reads every changed file and its diff on each push. troupe#283's size would take a few hundred
  turns.
- Not here: a house rule on file length, which would make reviews cheaper (several files across the three
  repositories are over 2,000 lines, `scripts/guard.py` among them). That's #271.
- Open pull requests get the coverage check on their next review run. The rulesets don't change: `claude review
  completed` is already required.
