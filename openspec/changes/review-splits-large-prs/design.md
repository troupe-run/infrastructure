# Design

## Context

`.github/workflows/claude-review.yml` currently runs one `claude review` job, with these steps:

1. Write each changed file's diff, and make `files.json`.
2. Read the conversations.
3. Run Claude once.
4. Name the denials.
5. Measure coverage.

After it come `resolve review conversations` and `claude review completed`, the required check. The coverage step
also decides which files count as source and test for #282's floor. It decides this after the session, so Claude
isn't told which files it may skip (review-coverage-floor design D2).

proposal.md's table holds what the runs show: sessions end by themselves, and none ran out of turns. A session that
commits to the list reads about 150 Reads. One that doesn't stops within a minute. So this design has to deal with
both a session that stops early and a list too big for one session, and the follow-up round is what deals with the
first.

Two things carry over from earlier changes:
- **Probe results (#274).** One Read without a limit stops at about 22 to 41 KB. Each target lists Reads of at most
  20,000 bytes.
- **Trust.** Claude has Read, Grep, Glob, `gh pr view`, `gh pr diff`, `gh issue view` and the inline-comment tool. It
  can't write a file, so nothing it does can touch `RUNNER_TEMP` or an artifact.

## Goals / Non-Goals

**Goals:**
- Every changed source and test file is read in full by some session of the run, measured from tool calls.
- A session that stops early costs at most two follow-up rounds, not a bypass.
- The pull request sees one review: one summary, with inline findings, resolves and re-tiers that can't conflict.
- Small pull requests behave as now: one session.

**Non-Goals:**
- Carrying coverage across runs (#280). This design's records are per run. #280 can extend them, keyed by blob hash.
- Making a session not stop early, for example by changing the model or adding effort flags. Both are out of scope.
  The follow-up round catches the session whatever the cause.
- Rereading data to check it's well formed. That's left to the tests that use the data.

## Decisions

### D1. Parts of at most 40 Reads, at most 6 parts

`PART_READS = 40`, `MAX_PARTS = 6`, declared in the plan step.

- **Why 40.** The failed sessions read 1 to 39 files before stopping. Sessions that committed read 150 Reads. A
  narrower list makes "read all of these" a short task, which is what we want each session to do.
- **When there's more.** Past 6 × 40 = 240 Reads, the parts grow evenly instead of adding sessions, which bounds the
  cost of one run.
- **How files are packed.**
  - Each file's targets stay together.
  - Files are taken in path order, so one folder's files tend to share a part. A test and its module may still land
    in different parts, and that's what the uses search is for.
  - A new part starts when adding the next file would pass 40 Reads, unless the part is empty: one file larger than
    40 Reads gets a part of its own.
- **Alternatives considered.**
  - One part per folder, which gives uneven sizes and no bound on how many parts there are.
  - A larger part, around 100 Reads. The evidence says size isn't what stops a session, so the smaller part costs
    little and makes each session's task shorter.

### D2. Files are sorted into kinds before the session starts, so Claude is told what to read

The plan step sorts each listed file with a line to read into source and test, prose or data. It does this with the
declared list that #282 put in the coverage step, which now moves to the plan step. Claude's prompt names its
must-read list, the prose it should read, and the data left to its tests.

This reverses #282's D2, which kept Claude from seeing the classes. That was safe because the classes didn't decide
what Claude was asked to read. Now they must: a part's list *is* its classes. Telling Claude what to read changes
nothing about trust. Coverage is still measured from tool calls, and a pull request's author can't move a file
between kinds without renaming it, which the review sees.

The list:
- **Prose:** suffixes `.md`, `.mdx`, `.txt`, `.svg`; names starting `LICENSE`; the top folder `openspec/`.
- **Data:** suffixes `.json`, `.jsonl`, `.ndjson`, `.csv`, `.tsv`; a file with no suffix in a `fixtures/` folder,
  which is how troupe's recorded streams are named (for example `fixtures/claude/stream-error`).
- **Configuration that isn't data:**
  - the names `package.json`, `tsconfig*.json`, `deno.json` and `composer.json`;
  - any file under `.github/`;
  - any file under `tofu/` (`tofu/required-checks.json` decides what blocks a merge).
  JSON that configures behaviour has no test that "uses" it the way a fixture has, so the conservative choice is to
  read it. The owner confirmed this list (2026-11-11).
- **Everything else** is source and test.

Two changes from #282's list:
- `fixtures/` no longer makes every file in it data. A `.py` there is code now.
- `.json` under `.github/` or `tofu/` counts as code.

Both make the check stricter, never looser.

JSON elsewhere that configures a tool stays data: `.claude/settings.json` (the guard's Claude Code hooks),
`.mcp.json`, `.claude.json`, `renovate.json` and the like. Claude's review of #299 raised it as a decision, and the
owner chose to leave them as data (2026-11-12): the guard's own tests and the owner's review cover them.

### D3. Data stays data only if something that isn't data names it

For each data file, the plan step runs `git grep -F -l` over the checkout for the file's name, then for the name of
its folder. It doesn't count a match in:
- the file itself;
- any other data file;
- anything under `openspec/`, since a proposal mentioning a fixture isn't a use.

If nothing names the file or its folder, it counts as source and test, and the summary says "nothing names it".

The folder's name counts as a match because troupe loads fixtures by folder, for example
`fixtures/responses/<case>/replies.json`. That's a permissive test: a folder called `responses` is likely named
somewhere. It's still enough to catch a stray export or an orphaned recording. The owner chose the file or folder name over
the file name alone (2026-11-11). It does this at no cost, and it can
only add files to the must-read list.

Alternatives considered:
- An explicit marker, such as a `.review-data` manifest. It needs every repository to maintain one, and it's a list
  that the pull request itself can widen.
- Running the tests to see which files they open. That's too heavy for the review, and CI already runs them.

### D4. Jobs: plan, parts, follow-up, report, check

```
gate ─▶ plan ─▶ review (matrix: parts)
     ─▶ plan follow-up 1 ─▶ follow-up 1 (matrix, if any)
     ─▶ plan follow-up 2 ─▶ follow-up 2 (matrix, if any)
     ─▶ resolve and report ─▶ claude review completed
```

- **`plan the review`.** It checks out, writes the diffs and `files.json` (now with each file's kind and part), and
  works out each part's Reads and turn limit.
  - It uploads the plan as the artifact `review-plan`.
  - It outputs the matrix (`parts`: a list of `{part, of}`) and the plan's digest.
  - The step that checks the model moves here, so it fails once rather than once per part.
- **`claude review (part n of m)`.** One matrix entry per part, with `fail-fast: false`.
  - It checks out, downloads `review-plan`, checks the digest, and copies the plan into the workspace (where Claude
    reads it) and into `RUNNER_TEMP` (where the measurement reads it).
  - It reads the conversations, runs Claude on its part's prompt, names denials, and measures this session's Reads.
  - It uploads `review-record-<round>-<part>`: covered line numbers per target path, the structured output, and the
    record's status (`measured` or `unknown`).
- **`plan follow-up 1` and `plan follow-up 2`.** Each downloads every record so far and the plan, and takes the
  union. They run one script, pinned once and held equal by the tests.
  - It outputs a follow-up matrix over the source and test files not yet read in full, split as in D1, or an empty
    one.
  - A missing record, or one that's `unknown`, makes its whole part's files unread. So the follow-up re-reads them,
    and coverage stays `unknown` only if the follow-up's record is also missing.
- **`claude review (follow-up r: n of m)`.** The same job body as the review job, with round 2 or 3, run only when
  its matrix isn't empty. GitHub Actions has no loop over jobs, so each round is its own pair of jobs.
- **`resolve and report`.** This is today's resolving job, widened.
  - It downloads every record, applies each session's `resolve` and `retier` under D7, and posts the one summary
    comment (D6) with the review App's token.
  - It writes the coverage table to the run's summary, and outputs `coverage`, `code` and `unread` for the check.
- **`claude review completed`.** The required check, with the same name and the same `needs` semantics, now on all
  the jobs above. Its script judges the outputs as in D9.

Records pass as artifacts of the same run. They're written only by our own steps, from `RUNNER_TEMP` and the
action's execution file. A pull request can't add an artifact to a run, and Claude can't write files. The artifacts
are retained for 1 day.

Alternatives considered:
- **Sequential sessions in one job,** with a fixed number of action steps, each gated on the one before it. Matrix
  jobs run in parallel, so a large review takes about as long as one session rather than six. And a fixed number of
  copies of the action step would be six copies of the same pinned block.
- **Matrix job outputs.** GitHub keeps only one entry's outputs, so they can't carry per-part results. Artifacts can.

### D5. The first part leads

Part 1's prompt holds today's whole review:
- `CLAUDE.md`;
- the pull request;
- checks 2 to 5 (OpenSpec tasks and deltas, the issue's "Done when", commit messages, `CLAUDE.md` and the guide);
- the prose list;
- its share of the source and test files.

Parts 2 and later, and every follow-up session, get the same opening:
- read `CLAUDE.md` and the pull request;
- check 1 (correctness) on their list only;
- the uses search for names changed in their files;
- the conversations, so they don't repeat a finding.

Their prompt says other sessions are reading the rest and doing the other checks.

Part 1's turn budget counts its prose Reads too. Prose doesn't count towards `PART_READS`, so a docs-heavy pull
request's lead can be larger than other parts. That's fine: prose isn't gated.

There's one prompt template, with the role-specific paragraphs chosen by the step that builds it. The template stays
the one place that says what the review checks (design D5 of claude-pr-review).

### D6. One summary, posted by the report job

The `--json-schema` gains a required `summary` string. The prompt's last paragraph asks for the summary there, not
in a comment. `Bash(gh pr comment:*)` comes off `--allowedTools`, so a session can't post a second top-level
comment.

The report job builds one comment with these sections:
1. A heading naming the head SHA.
2. Each session's summary under "Part n of m" or "Follow-up n of m". A missing summary says so.
3. The measured coverage: counts by kind, the files not read in full, and the data left to its tests (shortened past
   `SHOWN`).

Summaries are Claude's words and go into the comment as Markdown, as Claude's own comment did before. They aren't
used to decide anything.

Alternatives considered:
- A comment from every session, which is noisy and isn't "reported as one review".
- A final Claude session that merges the summaries. It costs another session, and it can drop findings.

### D7. Resolves and re-tiers are limited to the session's part

The report job knows each record's list. For a named conversation, it takes the thread's `path` from the snapshot in
`RUNNER_TEMP`. It acts on the request only when that path is on the session's list, or when it's on no session's list
and the session is part 1 of round 1.

A follow-up session's list covers only the files it was given. Its resolves count for those files.

If two sessions name the same thread, it's resolved once. A thread named to resolve by one session and to re-tier by
another is only resolved, as now.

The existing checks still apply: the thread must be the review's, must be open, and must be a must-fix or nit.

### D8. Concurrency per part number

Each matrix entry's group is `claude-review-<pr>-<round>-<part>`, with `cancel-in-progress: true`. A single group
can't be shared by entries of one matrix, because they'd cancel each other.

A newer push's part 1 cancels the older run's part 1, and so on for each part. If the newer run has fewer parts, the
older run's extra parts run to completion, posting findings on an older head. The next review sees those findings in
the conversations and resolves or keeps them. That's the cost of a group per part, which the owner accepted (2026-11-11)
over cancelling the older run through the API, which would need an `actions: write` token.

`plan the review`, the follow-up planners and `resolve and report` use `claude-review-<pr>-<job>` groups, so a newer
push replaces them as today. `completed` stays outside every group.

### D9. The check needs every source and test file

`completed` reads the report job's outputs:
- `coverage`: `complete`, `incomplete` or `unknown`;
- `code`: `none`, `all` or `unread`;
- `unread`: a list of `{path, read, kind}`.

It fails:
- for `unknown`, or any value it doesn't recognise;
- for `code=unread`, naming the source and test files (up to `SHOWN`, then "and n more").

It passes with one warning when only prose is unread. It passes with no warning otherwise. Data never appears in
`unread`, but the summary lists it.

The failure tells the agent to re-run the run, or to have the owner review the pull request and bypass the rules. It
no longer suggests a smaller pull request (#278, option C, not chosen).

#282's floor holds, since "every" includes "at least one". `none` (no source or test file changed) passes, as today.

### D10. Two follow-up rounds

The owner chose two rounds (2026-11-11), over one. If the second follow-up also stops early, the check fails and the agent re-runs the
run. A re-run starts from round 1, since nothing carries over until #280.

Any bound is arbitrary. Two rounds at most triple a large review's cost, and fewer runs need re-running by hand. #297's history suggests a second
session over a short list will usually read it.

### D11. Turn budget per session

A session's budget is `BASE_TURNS + TURNS_PER_READ × (its list's Reads)`, capped at `MAX_TURNS`, as now but per
session. The jobs' `timeout-minutes` stays 90.

## Risks / Trade-offs

- **[Cost]** A runner pull request now costs several sessions, plus maybe a follow-up. → That's bounded by
  `MAX_PARTS` per round and two follow-up rounds. It replaces paid re-runs and bypasses, which cost as much or more.
  #280 will cut repeat runs.
- **[A finding across parts]** A bug that only shows when two files in different parts are read together could be
  missed. → Folders stay together, the uses search reaches beyond each list, and part 1 checks the change as a whole
  against its spec. It's no worse than a single session that stops early, which is what happens today.
- **[Duplicate findings]** Two parallel sessions could post the same finding, since neither sees the other's
  comments. → Each session posts only on its own files. A duplicate is a nit the author resolves.
- **[A permissive data test]** The folder-name match in D3 lets most fixtures through. → That's the owner's call in
  #278: data is validated by its use. D3 only catches data with no use at all.
- **[Stale parts after a push]** An older run's extra parts can post on an old head (D8). → They show as outdated
  conversations, and the next review judges them.
- **[Workflow size]** The workflow grows by three jobs and the test file grows. → The scripts stay inline and pinned
  by hash, as now. Behaviour tests run the plan, follow-up and report scripts directly.
- **[Delivery timing]** troupe#379 is reviewed by the workflow on its own branch. → After the delivery merges to
  troupe's main, rebase #379 so it picks the change up (memory: guard rules reach open pull requests on rebase).

## Migration Plan

1. Merge here. The review of this pull request runs its own new workflow, since a pull request changing
   `claude-review.yml` is reviewed by its own copy. Its run is the first live evidence: parts, follow-up, one
   summary.
2. The owner approves the apply. The delivery puts the workflow in troupe and website, and
   `org-profile/CONTRIBUTING.md` in troupe-run/.github.
3. Rebase open troupe pull requests that need it, troupe#379 first.

Rollback: revert the commit and deliver again. `claude review completed` keeps its name, so required checks don't
change.

## Open Questions

None that change the specs or tasks. `PART_READS` and `MAX_PARTS` are constants to tune from the first runs' records.
