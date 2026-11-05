# Design

## Context

`.github/workflows/claude-review.yml` runs Claude once per pull request event, with `--max-turns 30`,
`timeout-minutes: 20` and no `--model`, so the action's default (`claude-sonnet-5-5`) is used. The prompt says "Read
the diff with `gh pr diff`" and lists five checks. Nothing after the session looks at what it read: the denial step
reads the action's execution file (`$RUNNER_TEMP/claude-execution-output.json`) only for `permission_denials`, and
`claude review completed` passes when the review and resolving jobs succeeded.

What troupe#283's runs actually did (`gh run view <id> --log`, 2026-11-04):

| Run | Turns used (of 30) | Session time | Cost | Denials |
| --- | --- | --- | --- | --- |
| 41782433539 | 13 | 25.6 s | $0.19 | none |
| 41782688844 | 9 | 15.2 s | $0.08 | none |
| 41784579003 | 14 | 28.1 s | $0.13 | none |
| 41787275514 | 12 | 18.9 s | $0.10 | none |

So no limit was hit. The session chose to stop. A `gh pr diff` of 9,000 lines is also more than one Bash result
shows, so even a willing session couldn't read it that way. See proposal.md for why this matters.

Constraints that shape the approach:

- Claude's tools stay as they are: Read, Grep and Glob in `./**`, and the `gh` reads and comment tools.
- What blocks a merge is GitHub's, not Claude's: a required check or an open conversation (spec: pr-review).
- The execution file lives in `RUNNER_TEMP`, outside the workspace. Claude can't Read it, and it has no tool that
  writes, so it's a record of the session that the session can't change.
- A pull request that changes this workflow is reviewed by its own copy (memory: a review change tests itself), so
  this change's pull request is the first live test of what it adds.

## Goals / Non-Goals

**Goals:**

- A passing `claude review completed` means the session read every changed file and diff on the list, measured, not
  claimed.
- The review is pointed at the code around a change, not only the change: whole files, and the uses of what changed.
- A large pull request gets enough turns and time to read its diff, up to a cap that's declared in one place.
- Changing the review's model is a one-line OpenTofu change.

**Non-Goals:**

- Judging the review's quality. Reading a diff doesn't mean understanding it. The measure is a floor that a skim
  can't pass, not proof of a good review. The owner's review is still the gate.
- Splitting one review across several jobs or sessions (by area, or commit by commit). If pull requests often hit the
  cap, that's a follow-up issue with the measurements to size it.
- Reviewing only what changed since the last review. Each run reads the whole diff, as it reviews the whole head
  today.
- Gating on call sites. Knowing which unchanged files use a changed name needs analysis for each language (Python,
  TypeScript, OpenTofu). A guess at it would be a poor merge gate, so the prompt asks for call sites and the summary
  reports what was searched and read (D7a). A gate on it would be a follow-up issue.
- A house rule on file length. It would make reviews cheaper, but this change is correct without it, since coverage
  counts the lines actually returned. Today `scripts/guard.py` (about 4,516 lines, in all three repositories), troupe's
  `error.schema.json`, website's schema fixtures and a plan doc, and infrastructure's `plan-pr96.txt` fixture are over
  2,000 lines. That's #271.

## Decisions

### D1. Measure coverage. Don't raise limits alone or trust the summary

Raising `--max-turns` alone wouldn't have changed #283, which used under half its turns. Asking Claude to report
coverage in its structured output would be its own word again, which is the thing that failed. So the measure comes
from the execution file. The action writes it from the SDK's messages, and Claude can neither reach nor write it.

Alternative considered: have the prompt tell Claude to post a must-fix naming what it didn't read. That's still
Claude's judgement of itself, and #283's sessions said what they hadn't read and passed anyway.

### D2. The list of what to read, with per-file diffs made with git

The checkout already holds the whole branch as it would merge, so the full source is there for Read and Grep. What
the review lacks is the list of what changed and a diff it can read whole. A step before the review (after the
checkouts, before the action) writes:

- `.review-diff/<path>.diff` for each changed file: `git diff --no-color --no-ext-diff --no-textconv --text -M
  HEAD^1 HEAD -- <path>`. `--text` and `--no-textconv` keep a `.gitattributes` the pull request brings (`*.py -diff`,
  `binary`, a `diff=` driver) from hiding its text behind "Binary files differ" (#274's review);
- `.review-diff/files.json`: each changed file's path, status, and its **targets**, the things that must be read,
  each with its line count, or the reason it needs none:

  | Status | Targets |
  | --- | --- |
  | added | the file in the checkout (its diff is the same text, so isn't a target) |
  | modified, renamed | the file in the checkout, as it is now, and its `.diff`, which also shows the removed lines |
  | deleted | its `.diff`, the only record of what went |
  | binary, or on `REVIEW_SKIP` | none, with the reason |

  A changed file under a path the action restores from the base before Claude starts (`.claude`, `.mcp.json`,
  `.claude.json`, `.gitmodules`, `.ripgreprc`, `CLAUDE.md`, `CLAUDE.local.md`, `.husky`: `SENSITIVE_PATHS` in the
  pinned action's `src/github/operations/restore-config.ts`) is read as the action's copy of the pull request's
  version, `.claude-pr/<path>`, counted from the committed blob: at its own path Claude finds the base's copy
  (#274's review). If the action stops making that copy, the Read fails and coverage fails, which is the safe way.

  Each target also lists its `reads`: consecutive `offset`/`limit` chunks of at most `READ_CHUNK_BYTES` (a longer
  line on its own) that cover it, for the session to make exactly. #274's third and fourth reviews showed wording
  alone isn't enough: one read a 60 KB doc with a single capped Read, and one took modified files' diffs for the files
  (7 of 14 read in full, while its summary said all 14). The plan turns "read it all" into a list to work through;
  coverage is still measured, not trusted (owner, 2026-11-04, option 1 after option 3 failed).

  A copy goes to `RUNNER_TEMP` for the coverage step, as `.review-threads.json` does, so a pull request can't plant a
  list.

The checkout is GitHub's merge commit (`refs/pull/<n>/merge`). The review's checkout goes from `fetch-depth: 1` to
`2`, so `HEAD^1`, the base's tip, is present. This diff is the pull request as it would merge, which is what the
review reviews. It has no size cap, unlike `gh pr diff`, which GitHub refuses past 20,000 lines, and the files API,
which leaves out large patches. The step removes any `.review-diff/` the checkout holds before writing.

Needing nothing, each with its reason in `files.json`: binary files, which are those whose committed blob has a NUL
byte in its first 8,000 bytes, git's own test, and never what `.gitattributes` says (#274's review); and one declared
skip list, `REVIEW_SKIP`, in the step:

- `uv.lock`, `package-lock.json`, `.terraform.lock.hcl`;
- `terraform.tfstate` (encrypted state that CI commits).

It matches by file name, wherever the file is, so a lockfile in a subdirectory needs nothing read too.

The list is a constant in the step, pinned by the workflow's test. Adding a path is a reviewed change to the
workflow (owner, 2026-11-04: every file but a skip list).

A pull request with no listed file, such as a lockfile-only one, still gets a review. Its coverage is complete by
definition.

### D3. What counts as read

The coverage step (after the review step, `if: ${{ !cancelled() }}`) reads the execution file:

1. For each assistant message's `tool_use` block named `Read`, it takes `input.file_path` and resolves it against
   the workspace. A path that resolves to a target on the list (a changed file in the checkout, or its `.diff`)
   counts towards that target. Any other path inside the workspace counts towards the call-site report (D7a), not
   towards coverage.
2. It pairs each with the `tool_result` that has the same `tool_use_id`. A result with `is_error: true`, or none,
   counts for nothing.
3. The lines a Read covered are taken from the line numbers at the start of each line of the result's text
   (`<n>` then a tab; `<n>→` is accepted too, an earlier format): what was actually returned, not what was asked for.
   The result's content is a string, or a list of text blocks whose texts are joined. So the default limit, a truncation or an offset past the end all
   count as they really happened. A result whose lines don't parse counts for nothing. That errs towards "not read",
   never towards "read".
4. A target is read when the union of its covered lines is `1..N`, where `N` is its line count from the
   `RUNNER_TEMP` list, counted as Read numbers them: split on newlines, without the empty line after a final
   newline, which Read numbers too but isn't required. A file is **read in full** when every one of its targets is read; **in part** when any line
   of any target is covered; **not read** otherwise. A file with no targets is complete.

The step prints only paths and counts, never a result's text. It writes a table to `GITHUB_STEP_SUMMARY` (paths
escaped for Markdown) and sets two job outputs: `coverage` (`complete`, `incomplete` or `unknown`) and `unread` (a
JSON list of `{path, read}` for each file not read in full). A missing or unparseable execution file gives `unknown`,
with every listed file in `unread`. The step itself never fails the job: the `completed` job decides.

The execution file's shape (assistant `tool_use` blocks, user `tool_result` blocks, the line-number prefix of Read's
output) is checked before the step is written (task 1.1), and again on this change's own pull request, whose review
runs the new step.

### D4. The `completed` job fails on coverage

`claude review completed`'s one step gains a check after its current ones. Once the review and resolving jobs
succeeded, it reads `needs.review.outputs.coverage` and `unread` from `env:`. Anything but `complete` fails with one
escaped `::error`. It names each file not read in full (up to 50, then "and n more") and says what to do:

- re-run the run (`gh run rerun <id>`), since a session may read more on another try;
- make the pull request smaller, if the review ran out of turns;
- or have the owner review it by hand and bypass the rules.

A bot's or fork's pull request still passes before this step, as today. A failed check, not a must-fix conversation,
is chosen because a fixed step decides it from the execution file, so neither Claude nor a reply can argue it away.
A must-fix would also need a later review to resolve it, which on the same head means a re-run anyway. (The owner
asked what a failed check involves, on 2026-11-04. If they'd rather have the conversation too, it's an extra step in
the resolving job and doesn't change D2 or D3.)

### D5. The turn budget and the timeout

A step before the review counts the Reads the list plans (D2's `reads`, one per chunk of at most `READ_CHUNK_BYTES`)
over every target, and
sets `max_turns = min(40 + 2 × reads, 400)`. `claude_args` reads it as `--max-turns ${{ steps.diff.outputs.max_turns
}}`. The value is an integer the step computed, never pull request text. Two turns per Read leaves room for searches,
call sites and findings. Read calls made in parallel in one turn make the real need lower. The cap of 400, with the
timeout raised from 20 to 90 minutes, bounds a runaway review's cost and time. A pull request too big for that fails
D4's check, naming what wasn't read.

How much one Read returns is Claude Code's, not something the prompt sets, and it's a token cap, not a line count
(Probe results): a Read with no `limit` stops at about 25,000 tokens, which was about 41 KB of short lines and about
22 KB of long ones. So the estimate is by size. `READ_CHUNK_BYTES` is 20,000, below both, so the estimate errs
towards more turns. The budget is only an estimate: if it's wrong, it's too generous or too tight, and too tight
shows as a failed check naming files, never as a false pass, because D3 counts the lines actually returned.

The base (40), the per-Read amount (2), the cap (400) and `READ_CHUNK_BYTES` are named constants in the step, pinned
by the test.

A run that a reply to a must-fix starts is the same review a push's run is (spec: pr-review, "The review judges a
reply to one of its must-fixes when it's posted"), so it gets the same list, budget and timeout, and reads the whole
pull request again: whether a reply settles a must-fix is judged against the code. Its coverage is measured and shown
in its run's summary, but enforced only through a push's run, since GitHub counts only a pull request event's run for
`claude review completed` (review-completed-check, Probe results). The owner chose this over a smaller budget for
reply runs, which would have changed that requirement (2026-11-04, on #274's review).

### D6. The model is a repository variable, declared once in OpenTofu

A new `tofu/review.tf` holds `local.review_model = "claude-sonnet-5-5"` and a `github_actions_variable`
`CLAUDE_REVIEW_MODEL` for each of troupe, infrastructure and website (a `for_each` over the three; the infrastructure
App already has Variables write on all three, as `board.tf` and `dependabot_dispatch.tf` show). It's a repository
variable rather than an org one, following the existing pattern and keeping the App's org permissions as they are.

The workflow checks it in a step before the review: `vars.CLAUDE_REVIEW_MODEL` is passed through `env:` and must match
`^claude-[a-z0-9]+(-[a-z0-9]+)*$`. If it's unset or anything else, the step fails with an `::error` naming the
variable, so the review fails and so does `claude review completed`. There's no default in the workflow, so the value
lives in one place (an unset variable is a missing declaration, not "use Sonnet"). The validated value goes to
`claude_args` as the step's output.

Order: this change's own pull request is reviewed by its own copy of the workflow, before any apply. So the owner
sets the variable on infrastructure by hand first (`gh variable set CLAUDE_REVIEW_MODEL -R troupe-run/infrastructure
--body claude-sonnet-5-5`, which the guard leaves to the owner), and `review.tf` adopts it with an `import` block.
troupe's and website's are created in the apply that delivers the workflow. The delivery `depends_on` them, so no
delivered copy runs without its variable.

### D7. The prompt

The prompt changes in three places:

- "Read the diff with `gh pr diff`" becomes: read `.review-diff/files.json`, then read every target it lists in full
  with Read, in parallel where you can, before writing findings. That's an added file whole, a modified or renamed
  file whole and its `.diff`, and a deleted file's `.diff`. Each target's `reads` lists the Reads that cover it:
  make every one, with that `offset` and `limit`, and don't take a file's diff for the file. On a later run, read
  them all again. `gh pr diff` is no longer the way to read it.

  #274's second review read `docs/development-workflow.md` (60 KB) with one Read that stopped at the token cap; the
  prompt then said to read on from the next line (option 3), and the fourth review still read 7 of 14 files in full.
  So the prompt now hands over D2's plan rather than asking the session to notice it stopped short (owner,
  2026-11-04).
- For each changed signature, removed or renamed name, or changed behaviour, search the checkout for its uses with
  Grep and read them (D7a).
- A review that hasn't read everything listed isn't a clean review. Don't say it is, and don't stop at the task list
  or the file list.
- The summary ends with a coverage line: how many listed files it read, any it didn't, and which call sites it
  checked.

Claude's tools don't change. `Bash(gh pr diff:*)` stays, since it does no harm and reading the diff that way is
still allowed.

### D7a. Call sites: asked for and reported, not gated

A change that breaks its callers shows only in the files that call it, and those are often unchanged. Which files
they are can't be known in general without analysis for each language, so it isn't enforced. From the same execution
file as D3, the coverage step lists, under the coverage table:

- each Grep call's `pattern` (cut to 100 characters, escaped), and whether it returned an error;
- each file the session read that isn't a target: path only.

That's data for the reader, and for the owner deciding whether the review looked beyond the changed files. It has no
effect on `coverage`. A gate on call sites (for example, a list of callers worked out for each language) would be a
follow-up issue, sized by what these reports show.

### D8. Tests

`scripts/tests/test_claude_review_workflow.py` gains:

- pins for the new steps' shape and their place in `problems()`, and named cases in
  `test_each_way_the_workflow_can_go_wrong_is_named`: the coverage step removed, made `continue-on-error` in a way
  that hides its outputs, reading `structured_output`; `completed` not reading `coverage`; the model taken straight
  from `vars` into `claude_args`; `--max-turns` fixed again; `fetch-depth` back to 1;
- tests that run the diff step on a scratch git repository with a merge commit: a modified, an added, a deleted, a
  binary, a renamed and a skip-listed file, each with the targets D2's table gives; a file larger than
  `READ_CHUNK_BYTES` and the `reads` it gives; a planted `.review-diff/`;
- tests that run the coverage step on execution files: every target read; one file read in part across two Reads
  that leave a gap; a modified file whose diff was read but not the file; a Read with `is_error`; a Read outside the
  list, which appears in the call-site report and not in coverage; a Grep's pattern in the report; no execution file;
  a malformed one. Among them, **a session whose result text says "Not checked: I did not read the implementation",
  which read only `tasks.md`, leaves `coverage=incomplete` naming the files, and the `completed` step then fails**
  (#268's "Done when", item 4);
- tests that run the `completed` step with each `coverage` value, and that a hostile path stays inside one error;
- the model step with an unset, a valid and a hostile value;
- a docs test that "Claude's review" says what a passing review means.

## Risks / Trade-offs

- [Reading whole modified files costs more than reading diffs] → Accepted (owner, 2026-11-04): a diff can't show a
  change that's wrong for its surroundings. A file-length house rule (#271) is what makes it cheaper.
- [A review reads every changed file and still misses a broken caller] → Call sites are asked for and reported
  (D7a), not gated. The report shows when a review didn't look.
- [Cost goes up for large pull requests, on every push and every reply to a must-fix] → The cap bounds it. The model is one variable away from a
  cheaper or dearer one. If it's too much, a follow-up can review only what changed since the last completed review.
- [A session reads every diff and still reviews badly] → Accepted. This is a floor (Non-Goals). The owner's review is
  still the gate.
- [The execution file's format changes in a newer action] → The step errs towards "not read", so a format change
  fails the check loudly rather than passing a skim. A test with a real execution file's shape catches it at the
  action's next update.
- [Read cuts a line longer than its per-line limit] → The line still counts as read. A minified or generated file
  with very long lines belongs on the skip list.
- [A pull request too large for the cap can never pass alone] → Its message says so, and the owner can bypass after a
  review by hand. If that's common, the follow-up in Non-Goals is the fix.
- [The coverage check reaches open pull requests on their next review run] → The rulesets don't change. A pull
  request whose last review predates the change keeps its check until its next push.

## Migration Plan

1. The owner sets `CLAUDE_REVIEW_MODEL` on infrastructure (D6) before this change's pull request is opened.
2. The pull request's own review runs the new workflow. Its coverage summary and check are the live test.
3. After the merge, the plan shows the imported infrastructure variable, the two new variables, the two deliveries of
   `claude-review.yml`, and nothing else. The owner approves the apply.
4. Rollback: revert the workflow's commit. The variables are harmless without it.

## Open Questions

None that change the specs. The constants in D5 may need tuning once real large reviews have run. Tuning them is a
reviewed change to the workflow.

## Probe results

Task 1.1, 2026-11-04. Claude Code 2.1.316 run locally as the action runs it (`claude -p --output-format stream-json
--verbose --setting-sources user --allowedTools "Read(./**),Grep(./**)"`, model `claude-sonnet-5-5`), in a scratch
directory of generated files. Only fields and counts are recorded here, no file contents.

**The execution file is the same messages.** At the pinned SHA, `base-action/src/run-claude-sdk.ts` pushes every
message the Agent SDK's `query()` yields into a list, and `base-action/src/execution-file.ts` writes that list with
`JSON.stringify` to `$RUNNER_TEMP/claude-execution-output.json`. The action depends on
`@anthropic-ai/claude-agent-sdk ^0.3.311`, so its Claude Code may differ from 2.1.316 in Read's limits. D3 counts what
was returned, so a difference can only make coverage lower, never pass a skim.

**Shapes:**

- A tool call is a block in an `assistant` message's `message.content`: `{type: "tool_use", id, name, input, caller}`.
  Read's `input` is `{file_path}` (absolute), with `offset` and `limit` when given. Grep's is `{pattern, path,
  output_mode}`.
- Its result is a block in the next `user` message's `message.content`: `{type: "tool_result", tool_use_id, content}`,
  with `is_error: true` only on an error. `content` was a string in every case.
- Read's text numbers each line as `<n>` then a tab (`1\tline 1 ...`), from `offset` (or 1).
- The `user` message also carries `tool_use_result`; for a Read that succeeded it's `{type, file: {filePath, content,
  numLines, startLine, totalLines, truncatedByTokenCap?}}`. D3 uses the numbered text, which is in the message
  itself, not this.

**What Read returned:**

| File | Call | Result |
| --- | --- | --- |
| 2,500 lines, ~20 bytes each (51 KB) | no `limit` | lines 1 to 2,004 (`truncatedByTokenCap: true`) |
| the same | `offset 2001, limit 600` | lines 2,001 to 2,501 (the last is the empty line after the final newline) |
| 3,000 lines of one character | no `limit` | all 3,001 lines, in one Read |
| 2,500 lines of ~100 bytes (252 KB) | no `limit` | lines 1 to 216 (`truncatedByTokenCap: true`) |
| the same | `offset 1, limit 2500` | error: "exceeds maximum allowed tokens (25000)" |
| 3,000 lines of ~400 bytes (1.2 MB) | no `limit` | error: "exceeds maximum allowed size (256KB)" |
| the same | `offset 1, limit 100` | error: "exceeds maximum allowed tokens (25000)" |
| a missing file | no `limit` | error: "File does not exist" |

So there's no line limit: a Read with no `limit` stops at a token cap, and one whose `limit` asks for more than 25,000
tokens, or a file over 256 KB read with no `limit`, is refused outright and returns nothing. The prompt says so (D7).
D5 estimates by size, not lines.
