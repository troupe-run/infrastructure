# Tasks

## 1. The execution file's shape (design D3)

- [x] 1.1 Run Claude Code locally in a scratch directory, the way the action runs it (`claude -p --output-format
  stream-json --verbose`, `--allowedTools "Read(./**)"`), on a prompt that reads a 2,500-line file once whole and
  once with `offset`/`limit`, reads a file large enough to meet any cap on one Read's output (many long lines), runs
  one Grep, and reads one missing file. Record in design.md, under a new "Probe results": the `tool_use` block's
  fields for Read and Grep, the `tool_result` block's `tool_use_id` and `is_error`, the line-number prefix of Read's
  text, how many lines a Read with no `limit` returned, and whether a large file hit a size or token cap and what it
  returned then. Set D5's chunk constant from it. Check the action's execution file is the same list of messages (its
  source at the pinned SHA, `base-action/`). Verify by quoting the fields and counts (never file contents) in the
  design, and amend D3 and D5 if any differ

## 2. The per-file diff (design D2, D5)

- [x] 2.1 Change the review job's checkout to `fetch-depth: 2`, and add the step "Write each changed file's diff"
  after the guide's checkout: it removes any `.review-diff/`, writes `.review-diff/<path>.diff` and `files.json` from
  `git diff -M HEAD^1 HEAD` with each file's targets and their line counts as D2's table says, copies `files.json` to
  `RUNNER_TEMP`, applies `REVIEW_SKIP` and the binary rule, and sets `max_turns` from the Reads needed and the D5
  constants. A diff that can't be made fails with an escaped `::error`. Verify `uv run scripts/check.py` passes
- [x] 2.2 Pin the step in `problems()` and add named cases to `test_each_way_the_workflow_can_go_wrong_is_named`
  (`fetch-depth` back to 1, `REVIEW_SKIP` or the constants changed, `--max-turns` fixed again or not from the step's
  output). Add tests that run the step on a scratch repository whose `HEAD` is a merge commit: a modified file (the
  file and its diff), an added one (the file only), a deleted one (its diff only), a binary, renamed and skip-listed
  file, a file larger than `READ_CHUNK_BYTES` and the Reads it counts, a planted `.review-diff/`, and nothing to read; each
  named for its outcome. Verify `uv run pytest scripts/tests/test_claude_review_workflow.py` passes

## 3. The model variable (design D6)

- [ ] 3.1 Ask the owner to run `gh variable set CLAUDE_REVIEW_MODEL -R troupe-run/infrastructure --body
  claude-sonnet-5-5` (owner-only). Verify `gh variable list -R troupe-run/infrastructure` lists it
- [x] 3.2 Add `tofu/review.tf`: `local.review_model`, a `github_actions_variable` for each of troupe, infrastructure
  and website, and an `import` block for infrastructure's. Add the troupe and website variables to the guard
  delivery's `depends_on`. Verify `tofu fmt -check` and `tofu validate` pass
- [x] 3.3 Add the step "Check the review's model" before the review: `vars.CLAUDE_REVIEW_MODEL` through `env:`,
  matched against D6's pattern, failing with an `::error` naming the variable, and the value as its output. Pass it to
  `claude_args` as `--model ${{ steps.model.outputs.model }}`. Pin it, add a named case for `vars` used in
  `claude_args` directly, and tests for an unset, a valid and a hostile value (`claude-x --allowedTools Bash`, a
  newline). Verify the tests pass

## 4. The prompt (design D7)

- [x] 4.1 Change the prompt as D7 says. Add a test that the prompt names `.review-diff/files.json`, tells the review
  to read every listed target in full, asks for the uses of changed names to be searched for and read, and no longer
  says to read the diff with `gh pr diff`. Verify it passes, and fails with each sentence removed

## 5. Coverage and the check (design D3, D4, D5)

- [x] 5.1 Add the step "Measure what the review read" after the review step (`if: ${{ !cancelled() }}`) as D3 and D7a
  say, with the job outputs `coverage` and `unread`, and in `GITHUB_STEP_SUMMARY` the coverage table and the
  call-site report. Raise the review job's
  `timeout-minutes` to 90. Pin both, and add named cases (the step removed, reading `structured_output` or the
  summary, printing a result's text, the timeout back to 20). Verify `uv run scripts/check.py` passes
- [x] 5.2 Add tests that run the step on execution files shaped as task 1.1 recorded: every diff read; one read in
  part across two Reads with a gap; a modified file whose diff was read but not the file (in part); a Read with
  `is_error`; a Read of an unchanged file, which is in the call-site report and not in coverage; a Grep whose pattern
  is in the report, and a hostile one that stays escaped; a session with no search, reported as none and not failing;
  a planted `files.json` in the workspace that differs from `RUNNER_TEMP`'s; no execution file; a malformed one. Each
  is named for its outcome. Verify the tests pass
- [x] 5.3 Add D4's step to `completed` and its `env:` (`COVERAGE`, `UNREAD`). Add tests that run it with `complete`,
  `incomplete`, `unknown` and no value, with more than 50 unread files, and with a hostile path that stays inside one
  error. Add the named cases for `completed` not reading `coverage`. Verify the tests pass
- [x] 5.4 Add the test #268 asks for: a session whose result text says "Not checked: I did not read the
  implementation line by line", which read only `tasks.md`, goes through the coverage step and then `completed`, and
  the check fails naming the unread files. Verify it passes, and that it fails when `completed`'s coverage step is
  removed
- [x] 5.5 Update the workflow's header comment and the `review` and `completed` jobs' comments for D2 to D6. Run
  website's `npx vitest run tests/unit/workflow-node-version.test.ts` and troupe's `uv run scripts/check.py` with the
  new `claude-review.yml` in place in scratch clones, as the header asks. Verify both pass

## 6. Docs (development-workflow delta)

- [x] 6.1 In `docs/development-workflow.md`, "Claude's review": say what a passing `claude review completed` means
  (the head's review finished and read every listed file and diff in full) and doesn't (no bugs, call sites checked,
  or no need for the owner's review), what the list leaves out, where the call-site report is, and what to do when it
  fails for coverage. Update the paragraph on
  required checks that says what the review job is. Add a docs test that the section says what a passing review
  means. Verify it passes, and fails with the paragraph removed
- [x] 6.2 Check `CLAUDE.md` step 5 and the org's contributing guide (`org-profile/CONTRIBUTING.md`) for "the review of
  the last push has completed" and say there that it includes coverage, where they say what a passing check means.
  Verify `uv run scripts/check.py` passes

## 7. Plan

- [ ] 7.1 On the pull request, read `plan (pull request)`. Verify it imports infrastructure's `CLAUDE_REVIEW_MODEL`,
  adds troupe's and website's, and updates the two deliveries of `claude-review.yml` (and `.github`'s
  `CONTRIBUTING.md` if 6.2 changed it), and nothing else
- [ ] 7.2 Read this pull request's own review run. Verify its coverage table lists every listed file, its
  `claude review completed` reflects it, and its `--model` and `--max-turns` are as D5 and D6 say

## Workflow follow-up

- Open the draft pull request (`Closes #268`), act on Claude's review, mark it ready; the owner approves `plan (pull
  request)`.
- Archive on the branch before merging.
- After the merge and the owner's apply, check that a review in troupe and website reports coverage. Comment on #268
  with the PR and the archived change, and check its card says Done. If troupe#283 is still open, its next push gets
  the new review.
