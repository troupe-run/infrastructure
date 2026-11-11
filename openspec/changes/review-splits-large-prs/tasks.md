# Tasks

## 1. The plan sorts files into kinds and splits them into parts (design D1, D2, D3, D11)

- [x] 1.1 Add a `plan the review` job after `gate`, holding the checkout, "Check the review's model" and "Write each
  changed file's diff". The diff step and the model check move into this job. The `.org-guide` checkout stays in
  each review job.
  - In the diff step, declare `KINDS`: prose, data, and the configuration that isn't data, with D2's reason in a
    comment.
  - Give each entry a `kind` (`source and test`, `prose`, `data` or none), with a `why` when data was turned into
    source and test by D3.
  - Run D3's `git grep -F -l` check per data file, ignoring the file itself, other data files and `openspec/`.
  - Pack the source and test files into parts per D1 (`PART_READS = 40`, `MAX_PARTS = 6`). Part 1 also gets the
    prose.
  - Write `files.json` with `kind` and `part` per entry, and `parts` holding `{part, of, reads, max_turns}`.
  - Upload it as `review-plan` (retention 1 day). Output the `parts` matrix and the file's SHA-256.
  - Verify with `uv run pytest scripts/tests/test_claude_review_workflow.py -k plan` after 1.2.
- [x] 1.2 Add `Session`-style plan tests in `scripts/tests/test_claude_review_workflow.py`, each named for what its
  body checks, run on a merged scratch repository as `run_diff` does today:
  - **Kinds.** `.py`, `.yml` and `.astro` are source and test. `README.md`, `LICENSE`, `.txt` and
    `openspec/x/.openspec.yaml` are prose. `events.json`, a `.jsonl`, a `.csv` and an extensionless
    `fixtures/claude/stream-error` that a test names are data. `fixtures/conftest.py`, `package.json`,
    `tsconfig.base.json`, `tofu/required-checks.json` and `.github/x.json` are source and test. An empty
    `__init__.py`, `uv.lock` and a PNG have no kind.
  - **Data nothing names.** A JSON file named by no file is source and test with "nothing names it". One named only by
    another JSON file, or only under `openspec/`, is source and test. One whose folder a test names is data.
  - **Parts.**
    - 8 Reads make one part.
    - 130 Reads of source and test files make 4 parts of at most 40, each file in one part, folders together.
    - 400 Reads make 6 parts with no file dropped.
    - One 60-Read file gets a part of its own.
    - A prose-and-data-only pull request makes one part with no source or test file.
    - Each part's `max_turns` follows its own Reads plus part 1's prose.
  - **troupe#325's 39 files.** The source and test files land in 1 part, the 10 JSON schemas are data, and the 16
    `.py` files are source and test.
  - Move the diff step's hash pin into the plan job's pin.
  - Verify that `uv run pytest scripts/tests/test_claude_review_workflow.py` passes.

## 2. Each part is its own session, and records what it read (design D4, D5, D6, D8, D11)

- [x] 2.1 Make the review job a matrix over `needs.plan.outputs.parts` with `fail-fast: false`, named
  `claude review (part ${{ matrix.part }} of ${{ matrix.of }})`, with the group
  `claude-review-<pr>-1-${{ matrix.part }}`.
  - Before the action, add a step that downloads `review-plan`, checks its SHA-256 against the plan's output (failing
    if it differs), and writes it to `.review-diff/files.json` and `RUNNER_TEMP`.
  - The prompt names the session's own list, from the targets with `part == matrix.part`. It has a lead paragraph
    (part 1 of round 1: checks 2 to 5 and the prose) and a part paragraph (the others: check 1 and uses on its list;
    other sessions read the rest). The template stays the one place that says what the review checks.
  - The `--json-schema` gains a required `summary` string. The last paragraph asks for the summary there, naming each
    file on its list not read in full.
  - `Bash(gh pr comment:*)` comes off `--allowedTools`. `--max-turns` comes from the session's own part.
  - The coverage step measures only this session, writes `review-record-1-<part>.json` (covered lines per target,
    status `measured` or `unknown`, and the structured output from the action's output) into `RUNNER_TEMP`, and
    uploads it. It no longer writes the job outputs the check reads.
  - Verify with `uv run pytest scripts/tests/test_claude_review_workflow.py` after 2.2.
- [x] 2.2 Update the structural checks (`problems()` and the named-weakening cases):
  - The matrix, `fail-fast: false`, and the per-part group.
  - The digest check before Claude.
  - The tool list without `gh pr comment`, with a weakening case that adds it back, naming the tool.
  - `summary` required in the schema.
  - The record upload under `!cancelled()`.
  - Move the coverage step's pin.

  Add `Session` tests:
  - A session's record holds only its own Reads.
  - A failed Read counts for nothing.
  - An unreadable execution file gives status `unknown`.
  - The prompt test: the session's list is named; the lead and part paragraphs appear only in their roles; the
    summary goes in the structured output.

  Verify that `uv run pytest scripts/tests/test_claude_review_workflow.py` passes.

## 3. Two follow-up rounds read what the parts left (design D4, D10)

- [x] 3.1 Add `plan follow-up 1` (needs `plan` and `review`) and `plan follow-up 2` (needs follow-up 1), each
  `always()` once `plan` succeeded, running one script that downloads every `review-record-*` so far and the plan,
  and takes the union of covered lines.
  - A missing or `unknown` record leaves all of its part's files unread.
  - It packs the source and test files not read in full into follow-up parts per D1, and outputs that matrix, or `[]`.
  - Add the two follow-up matrix jobs: the same steps as 2.1 with round 2 or 3, the follow-up prompt paragraph ("an
    earlier session didn't read these"), and the group `claude-review-<pr>-<round>-<part>`. Each runs only when its
    matrix isn't empty.
  - Verify with `uv run pytest scripts/tests/test_claude_review_workflow.py -k follow` after 3.2.
- [x] 3.2 Add tests for the follow-up planner, each named for its outcome:
  - troupe#325's three attempts' records (33, 13 and 47 turns; 0 of 16 source and test files in full) give a follow-up
    over the 16 files.
  - Everything read gives `[]`.
  - Only prose unread gives `[]`.
  - A file whose diff was read in round 1 is still listed until the file itself is read.
  - A missing part record lists that part's files.
  - Round 3's planner, given round 2's record that left two files, lists those two.
  - Pin the planner's script, and check the two planners' scripts are equal.

  Verify that `uv run pytest scripts/tests/test_claude_review_workflow.py` passes.

## 4. One report and resolves limited to each part (design D6, D7, D9)

- [x] 4.1 Widen the resolving job into `resolve and report`, needing the review, both follow-up planners and both
  follow-up jobs.
  - It downloads every record, and applies each record's `resolve` and `retier` only for threads whose `path` is on
    that session's list. A thread on no list goes to part 1 of round 1 only. Each skipped one is named in a warning.
  - It takes the union of coverage, writes the run summary's table (file, change, kind, read, and why for D3), and
    posts one top-level comment with `gh pr comment --body-file`: each session's summary under its heading, a
    missing summary named, then the measured coverage.
  - It outputs `coverage` (`complete`, `incomplete` or `unknown`), `code` (`none`, `all` or `unread`) and `unread`
    (`path`, `read`, `kind`; source, test and prose only).
  - Verify with `uv run pytest scripts/tests/test_claude_review_workflow.py -k report` after 4.2.
- [x] 4.2 Add tests, each named for its outcome:
  - A part-2 resolve on a part-1 file is skipped with a warning.
  - A part-1 resolve on `README.md` is carried out.
  - A thread named by two sessions is resolved once.
  - Resolve beats re-tier across sessions.
  - The existing must-fix, nit and decision rules still hold.
  - The comment holds every summary and names a missing one.
  - The union counts a diff read in round 1 and the file read in round 2 as in full.
  - A missing record makes coverage `unknown`, naming the part.
  - Data never appears in `unread`.
  - Pin the script and update the job's structure checks.

  Verify that `uv run pytest scripts/tests/test_claude_review_workflow.py` passes.

## 5. The check needs every source and test file (design D9)

- [x] 5.1 Point `completed`'s `needs` and env at the new jobs and the report job's outputs. Rewrite its coverage part
  as D9:
  - `unknown` or an unrecognised value fails.
  - `code=unread` fails naming the source and test files (up to `SHOWN`).
  - Prose-only unread passes with one warning.
  - Otherwise it passes.

  Also:
  - The failure's fix says to re-run the run or ask the owner, with no "smaller pull request".
  - Update the comments at the top of the workflow and on the job, and remove the "Until #280" wording that says
    coverage is advisory.
  - A job that was cancelled or failed still fails as now. A follow-up job that was skipped because its matrix was
    empty counts as completed.
  - Verify with `uv run pytest scripts/tests/test_claude_review_workflow.py -k completed` after 5.2.
- [x] 5.2 Rewrite the `run_completed` tests:
  - `all` passes with no warning.
  - Prose unread passes with one warning.
  - `unread` fails naming only source and test files.
  - Sixty unread files say "and 10 more".
  - `unknown`, empty or garbage values fail.
  - A skipped empty follow-up passes.
  - A failed follow-up fails.
  - Source unread after round 3 fails, naming it.
  - troupe#283's shape still fails.
  - troupe#325's union of round 1 and a follow-up that read the 16 files passes.

  Add weakening cases:
  - the `unread` condition replaced by `False`;
  - a part's record dropped from the union;
  - coverage read from `summary`.

  Rename any test whose name still says the floor alone decides. Verify that
  `uv run pytest scripts/tests/test_claude_review_workflow.py` passes.

## 6. Docs say what a passing review means (development-workflow delta)

- [x] 6.1 Rewrite the coverage paragraphs of "Claude's review" in `docs/development-workflow.md`:
  - A pass means every changed source and test file was read in full across the run's sessions.
  - Which files are prose and data, and D3's rule.
  - How a large pull request is split into parts, with up to two follow-up rounds.
  - That it's one review with one summary.
  - What to do when the check fails: re-run, or ask the owner.

  Make the same point, more briefly, in `CLAUDE.md`, `README.md` and `org-profile/CONTRIBUTING.md` wherever they
  describe the check. Update the docs test's expected phrases. Verify that
  `uv run pytest scripts/tests/test_claude_review_workflow.py` passes, and that `grep -rn "Until #280\|floor"` over
  those four files shows no stale wording.

## 7. Whole-change checks

- [x] 7.1 Run `uv run scripts/check.py`: ruff, mypy `--strict`, the tests, and `openspec validate --strict`. Verify it
  passes, and cite its output.
  - Done 2026-11-12: all gates passed (ruff, ruff format, mypy --strict, 3132 tests passed and 14 skipped, tofu
    fmt, init and validate), and `openspec validate review-splits-large-prs --strict` is valid.
- [x] 7.2 Before delivery, run troupe's `uv run scripts/check.py` and website's
  `npx vitest run tests/unit/workflow-node-version.test.ts` with the new workflow in place, as the workflow's header
  asks. Verify that both pass, and cite their output.
  - Done 2026-11-11 on fresh clones of troupe's and website's main: troupe's `uv run scripts/check.py`
    passed (5643 passed, 16 skipped; all gates passed), and website's `npx vitest run
    tests/unit/workflow-node-version.test.ts` passed (8 of 8). Only the workflow's header comment changed after
    troupe's run.
- [x] 7.3 On this pull request's own review run, which runs the new workflow, record:
  - the plan's parts;
  - each session's turns and coverage;
  - whether follow-ups ran;
  - that one summary comment was posted;
  - `claude review completed`'s result.

  Verify by citing the run ID and its summary table in the pull request.
  - Done 2026-11-12, run 43031243264 on a3c9c64:
    - The plan listed 14 files (4 source and test, 10 prose, 0 data), as one part of 54 Reads with
      `--max-turns 148`.
    - The lead session read all 14 in full in 66 turns.
    - `plan follow-up 1` found 0 of 4 source and test files unread, so both follow-up rounds were skipped, as was
      `plan follow-up 2`.
    - `resolve and report` posted one summary comment, reporting 4 of 4 source and test files read in full.
    - `claude review completed` passed.
    - GitHub accepted the YAML anchors the three rounds share.
    - Not exercised live: more than one part, and a follow-up round. The behaviour tests cover those (troupe#325's
      and #318's shapes).

## Workflow follow-up

- Act on Claude's review of the last push, mark the pull request ready, archive the change on the branch, and have
  the owner merge it through the queue.
- The owner approves the apply. It delivers the workflow to troupe and website, and `org-profile/CONTRIBUTING.md` to
  troupe-run/.github.
- Rebase troupe#379 (and any other open troupe pull request that's waiting on a review) onto troupe's main once the
  delivery lands.
- Comment on #279 with the pull request and the archived change, close it, and check that its card says Done.
