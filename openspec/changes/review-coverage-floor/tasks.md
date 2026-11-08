# Tasks

## 1. The coverage step reports the floor (design D1, D2, D4)

- [x] 1.1 In "Measure what the review read", declare `NOT_CODE` (suffixes, `LICENSE*` names, an `openspec` first
  segment, any `fixtures` segment) with a comment giving D2's reason. Classify each entry: it counts as source or
  test when `NOT_CODE` doesn't match it and its targets hold at least one line. Write the `code` output (`none`,
  `read`, `unread`, `unknown`), and add `"code": true|false` to each `unread` item. Add the table's `Counts` column
  and the "Source and test files read in full" line, and the same count in the log line. Pass `code` on in the
  review job's `outputs`. Verify by running `uv run pytest scripts/tests/test_claude_review_workflow.py -k coverage`
  after 1.2
- [x] 1.2 Move `COVERAGE_SHA256`, add `code` to `REVIEW_OUTPUTS`, and add `Session` tests, each named for its outcome:
  `code` is `none` for Markdown and OpenSpec only, `read` when one module was read in full beside unread fixtures,
  `unread` when only the task list was read, and `unknown` with an unreadable record. Each `NOT_CODE` part doesn't
  count (`events.json`, a `.jsonl`, `README.md`, `LICENSE-CONTENT`, `openspec/x/.openspec.yaml`, `a/fixtures/b.py`).
  An unknown suffix (`.astro`) and a workflow `.yml` count. An empty added `__init__.py` doesn't meet the floor.
  `unread` items carry `code`. The summary shows the column and the count line. Verify that
  `uv run pytest scripts/tests/test_claude_review_workflow.py` passes

## 2. The check fails only on the floor or unknown coverage (design D3)

- [x] 2.1 In the `completed` job, add `CODE: ${{ needs.review.outputs.code }}` to the step's `env`, and rewrite the
  coverage part of its script as D3's four steps: an unmeasured or malformed `COVERAGE`/`CODE` fails, `unread`
  fails naming the source and test files, `incomplete` passes with one escaped `::warning` naming every unread file
  (up to `SHOWN`), and anything else passes. Update the job's comment to say coverage is advisory with a floor until
  #280. Verify that `uv run pytest scripts/tests/test_claude_review_workflow.py` passes after 2.2
- [x] 2.2 Move `COMPLETED_SHA256`, and add `CODE` to `COMPLETED_STEP`. Add the weakening cases: `CODE` dropped, `CODE`
  fixed to `read`, and the floor's condition replaced with `False`. Rewrite the `run_completed` tests:
  `incomplete`+`read` passes with one warning and no error, `unknown` fails, an empty or garbage `COVERAGE` or `CODE`
  fails, `unread` fails naming only the `"code": true` items, and `none` with unread prose passes with a warning.
  Sixty unread files warn with "and 10 more". A hostile path stays on the one warning line. Remove or rename any test
  whose name still says an incomplete review fails. Verify that
  `uv run pytest scripts/tests/test_claude_review_workflow.py` passes
- [x] 2.3 Add the evidence tests. troupe#318's four failing runs (78688ad: a module read in full, and 16 files in part
  or not read, including 4 test files; c6c651b twice and f6566be: 10 fixtures) go through the coverage step with
  `Session`, then the check, and each passes with a warning. troupe#283's shape
  (`test_a_review_that_says_it_didn_t_read_the_code_fails_the_check`) still fails, naming only the source files.
  Verify that `uv run pytest scripts/tests/test_claude_review_workflow.py` passes

## 3. The summary comment names what it didn't read (design D5)

- [x] 3.1 Change the prompt's last paragraph to ask the summary to name each listed file it didn't read in full, and
  add that phrase to `PROMPT` in the test. Verify that `uv run pytest scripts/tests/test_claude_review_workflow.py`
  passes, and fails with the phrase removed from the workflow

## 4. The docs say what a pass means for now

- [x] 4.1 Rewrite "Claude's review" in `docs/development-workflow.md`: the sentence that `test_guard_docs.py` pins,
  which becomes what a pass means until #280; which files count for the floor; that a warning is a pass, shown to the
  owner, and the pull request may be marked ready; that the comment's list is Claude's own account and the warning
  is measured; and what to do on a floor or `unknown` failure. Also update the required-checks paragraph (line 22).
  Update the pin in `scripts/tests/test_guard_docs.py`. Verify that
  `uv run pytest scripts/tests/test_guard_docs.py` passes
- [x] 4.2 Update `CLAUDE.md` step 5 ("which also means it read every changed file"), `org-profile/CONTRIBUTING.md`
  ("and read every changed file and diff it was given"), and the `claude-review.yml` row in `README.md`, so each
  says the check needs the review to have read the code, and that coverage short of complete is a warning until
  #280. Verify by `grep -n "read every changed" CLAUDE.md README.md org-profile/CONTRIBUTING.md
  docs/development-workflow.md`, which lists no claim that the check needs every file read

## 5. Whole-change verification

- [ ] 5.1 Run `uv run scripts/check.py` and `openspec validate review-coverage-floor --strict`. Both pass. Show the
  output
- [ ] 5.2 On this change's pull request, read its own review run (it runs the new workflow): the summary's table has
  the `Counts` column and count line, and `claude review completed` passes with or without a warning, or fails on
  the floor, as D3 says for what the run read. Quote the run's ID and its check result in the pull request

## Workflow follow-up

- After the merge, the plan should show only the deliveries of `claude-review.yml` to troupe and website, and
  `CONTRIBUTING.md` to troupe-run/.github. The owner approves the apply.
- Open runner pull requests rebase onto the delivered main, so a fresh `pull_request` run uses the new check.
- Archive on the branch before merging. After the merge, comment on #282 with the PR and the archived change, close
  it, and check that its card says Done.
