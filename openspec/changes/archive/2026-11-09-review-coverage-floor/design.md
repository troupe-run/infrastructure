# Design

## Context

See proposal.md, "Why". Here is how things work now, from `.github/workflows/claude-review.yml` at db509a1.

- **The diff step** ("Write each changed file's diff") writes `review-files.json`. Each entry has `path`, `status`,
  an optional `skipped` (skip list or binary, which means no targets), and `targets`. Each target has its `lines`.
  An added empty file has one target with 0 lines.
- **The coverage step** ("Measure what the review read", `continue-on-error`, pinned by
  `COVERAGE_SHA256`) gives each entry a state: `in full`, `in part`, `not read` or `nothing to read`. It outputs
  `coverage` (`complete`, `incomplete` or `unknown`) and `unread` (a JSON list of `{path, read}`), and writes the
  table to the run's summary. A target with 0 lines counts as `in full` without any Read, because the empty set is a
  subset of everything.
- **The review job** passes `coverage` and `unread` on as job outputs.
- **The `completed` job** (pinned by `COMPLETED_SHA256`) fails on anything but `complete`, with one `::error` that
  names up to `SHOWN = 50` files.
- **Tests:** `scripts/tests/test_claude_review_workflow.py` pins both scripts by hash, names the ways the check can
  be weakened (`test_each_way_the_workflow_can_go_wrong_is_named`), and runs both steps for real
  (`Session` for the coverage step, `run_completed` for the check). `scripts/tests/test_guard_docs.py:80` pins the
  docs' sentence "A passing review means the review read the code; it doesn't mean the code is right".

## Goals / Non-Goals

**Goals:**

- Decide the floor in the coverage step, which runs after Claude from a record Claude can't write. The `completed`
  job only judges what it's given (D1).
- Keep the decision about which files are code in one named place (D2).
- Fail closed on anything not measured (D3).

**Non-Goals:**

- Changing what's listed to read, the turn budget, or how a Read counts. Those stay as #274 built them.
- Posting the measured list as a comment. The warning and the run's summary carry it. Claude's own summary
  self-reports (D5).
- Any new state across runs. That's #280.

## Decisions

### D1. The coverage step decides the floor; the check judges it

The coverage step gains a third output, `code`:

| `code` | Meaning |
| --- | --- |
| `none` | No listed file counts as source or test (D2), so the floor has nothing to check |
| `read` | At least one file that counts was read `in full` |
| `unread` | At least one file counts, and none of them was read in full |
| `unknown` | `coverage` is `unknown` (the list or the record couldn't be read) |

Each item in `unread` gains `"code": true|false`, so the check can name the unread source and test files without a
second copy of the list. The review job passes `code` on as a job output. The `completed` job gets it as `CODE` in
`env:`.

Why not classify in the `completed` job? It would need the whole file list, not just the unread ones, to tell
`none` from `unread`. Then the list would live in two steps, or the job would read a file it doesn't have.

Why not classify in the diff step and write it into `files.json`? Claude reads `files.json`. A label there would
tell it which files it could skip without failing. The coverage step runs after the session, so nothing Claude does
can see or change the classification.

### D2. Which files count: a list of data and prose, everything else counts

The coverage step declares one constant, `NOT_CODE`, commented with its reason. It has three parts:

- **Suffixes:** `.md`, `.mdx`, `.txt`, `.json`, `.jsonl`, `.ndjson`, `.svg`. These are prose, data and recorded
  streams. The org's three repositories hold 1,265 `.md`, 316 `.json` and 16 `.jsonl` files on main, and troupe's
  recorded streams are `.jsonl`.
- **Names:** any file name that starts with `LICENSE` (troupe has 14 `LICENSE` files, and website has a
  `LICENSE-CONTENT`).
- **Directories:** a path whose first segment is `openspec`, or any path with a `fixtures` segment. OpenSpec holds
  proposals, specs and their `.openspec.yaml`. `fixtures/` holds troupe's recorded runs, which #318's ten unread
  files were.

A listed file counts as source or test when it isn't matched by `NOT_CODE`, and its targets hold at least one line.
Skip-listed and binary files have no targets, so they never count. An empty added file (`__init__.py`, `py.typed`,
`.gitkeep`) has 0 lines. It would otherwise read as `in full` with no Read, and meet the floor for nothing.

Why a list of what isn't code, rather than a list of code suffixes? A file of a kind the list doesn't name then
counts. That covers `.astro`, `.mjs`, `.css`, `.tf`, workflows, hooks with no suffix, and whatever a repository adds
next. So a gap in the list can only make the floor stricter, never quietly let through a review that read nothing.
The cost is small: the floor needs only one counted file read in full. An allow-list (`.py`, `.ts`, ...) would let a
pull request in a new language pass with no code read until someone noticed.

YAML outside `openspec/` counts. Workflows and the guard's config are code here. Matching is case-sensitive on the
suffix, so `README.MD` counts. That's harmless, because it fails closed.

### D3. What the check does, in order

After the existing bot, fork, gate and completion checks, which don't change:

1. If `COVERAGE` isn't `complete` or `incomplete`, or `CODE` isn't `none`, `read` or `unread`, it fails with
   "couldn't be measured, so nothing counts as read" for `unknown`, and "wasn't measured" otherwise. Under #281,
   `unknown` fails, and a missing or malformed value is an error, not a pass (learned rule: malformed input is an
   error).
2. If `CODE` is `unread`, it fails with `::error title=Review didn't read the code::`. The message names the unread
   items marked `"code": true` (up to `SHOWN`, then "and n more"), and keeps today's three ways forward.
3. If `COVERAGE` is `incomplete`, it prints one `::warning title=Review didn't read every changed file::` that names
   every unread item (up to `SHOWN`), says the check passes because coverage is advisory until #280, and exits 0.
4. Otherwise it passes, as today.

If `unread` can't be parsed, step 2 still fails, naming "files unnamed". Step 3 warns with "files unnamed", since
the floor was met. `complete` with `unread` for `CODE` can't happen, because complete means every file was read in
full. Step 2 runs first, so the check still fails if it ever does.

### D4. The run's summary

The table gains a column, `Counts`: `source or test`, `data or prose`, or `-` for a file with nothing to read. Under
it goes one line: "Source and test files read in full: n of m." When m is 0, it says "none changed, so the floor
doesn't apply". When none was read, it says "none, so `claude review completed` fails". The step's log line gets the
same count.

### D5. The summary comment names what it didn't read

One sentence of the prompt changes from "how many of the listed files you read in full, any you didn't" to "how many
of the listed files you read in full, and name each listed file you didn't read in full". The issue asks for the
review's comment to name them. Claude writes that comment before anything is measured, so the names are its own
account. The measured list is the check's warning and the run's table. The docs say so. `PROMPT` in the test gains
the new phrase.

### D6. Pins and tests

- `COVERAGE_SHA256` and `COMPLETED_SHA256` move. `REVIEW_OUTPUTS` and `COMPLETED_STEP["env"]` gain `code`/`CODE`.
- New weakening cases: `CODE` dropped from the check's env, or fixed to `read`, both named as "is given".
- The case that replaces `if coverage != "complete":` is retargeted at the floor's condition, so a script that
  skips the floor is named as unpinned.
- Coverage-step tests (with `Session`): `code` is `none`, `read` and `unread` as D1 says. Each `NOT_CODE` part is
  matched, an unknown suffix counts, and an empty added file doesn't count. `unread` items carry `code`. The table
  shows the column and the count line.
- Check tests (with `run_completed`): #318's four failing runs, rebuilt from their unread lists, pass with one
  warning and no error. troupe#283's shape fails, naming only source and test files. `unknown` fails. A missing or
  malformed `CODE` fails. `none` with unread prose passes with a warning. 60 unread files warn with "and 10 more". A
  hostile path stays inside the one warning line.
- Existing tests whose names say "fails" for an incomplete review are renamed or rewritten to what they now check.
  `test_a_review_that_says_it_didn_t_read_the_code_fails_the_check` keeps its name and outcome, because #283's
  shape still fails.

## Risks / Trade-offs

- [A review reads one small code file in full and skims the rest, and passes] → Accepted by #281 until #280. The
  warning names every unread file on the pull request's checks, the table is in the run, and the owner's review is
  still the gate.
- [A real code kind falls in `NOT_CODE`, such as code under a `fixtures/` directory, or a `.json` config that
  behaves like code] → It's still listed, read and warned about. It just doesn't meet the floor on its own. Changing
  the list is a reviewed edit to one constant.
- [An agent treats a warning as noise and marks ready] → The docs say a warning is a pass, and that it's shown to
  the owner. That's the decision.
- [The delivered copies lag] → troupe and website keep the blocking check until the owner approves the plan that
  delivers the new workflow. The migration plan below puts that apply first after the merge.

## Migration Plan

1. This change's own pull request is reviewed by its own copy of the workflow (memory: a review change tests
   itself). Its run shows the new table, and either a pass or a floor failure.
2. After the merge, the plan shows the deliveries of `claude-review.yml` to troupe and website, and
   `CONTRIBUTING.md` to troupe-run/.github, and nothing else. The owner approves the apply.
3. Open runner pull requests (troupe#318 and the like) need a fresh `pull_request` run to pick up the new check.
   Push, or re-run their latest run once the delivery is on their base. A re-run uses the workflow file at the run's
   own commit, so they need a rebase onto the delivered main first (memory: new required check blocks open PRs).
4. Rollback: revert the commit and apply. The old blocking check comes back.

## Open Questions

None that change the specs. `NOT_CODE` may want another suffix once more repositories are reviewed. That's a
reviewed one-line change.
