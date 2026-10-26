# Tasks

## 0. The owner's decisions and the issues

- [x] 0.1 Owner: choose how a denial is reported, how the guide is read, and the issue shape (design D1, D4). Done
      (owner, 2026-10-26): a report step that reads only the denials; a second, sparse checkout of troupe-run/.github;
      a new issue for the fix (#161, on the board), with #159 left open for its post-delivery checks
- [x] 0.2 Set #161's card to In Progress. Done: `gh issue view 161 -R troupe-run/infrastructure --json projectItems`
      shows In Progress (2026-10-26)
- [x] 0.3 Comment on #159: the fix is #161 (this change), so its first reviews in troupe and website check the new
      version, and its third check is met by troupe's release pull request #89, whose run 40302116098 skipped
      `claude review` without failing. Verify the comment shows with
      `gh issue view 159 -R troupe-run/infrastructure --comments`. Done: issuecomment-6414847490 shows (2026-10-26)

## 1. Real execution files (design D3)

- [x] 1.1 In an empty directory under the scratchpad, capture two runs with `claude -p --output-format stream-json
      --verbose --setting-sources user --allowedTools "Read(./**)"`. In the first, Claude is asked to fetch
      `https://github.com/troupe-run/.github/blob/main/CONTRIBUTING.md`, so it's refused. In the second, it's asked to
      read a file in the directory. Turn each into a JSON array, as `writeExecutionFile` writes it, and save them as
      `scripts/tests/fixtures/claude-execution-denied.json` and `claude-execution-clean.json`. Verify the first's
      `result` message has one `permission_denials` entry and the second's has none, with `jq`. Done: 1 (`WebFetch`,
      the guide's URL) and 0. The prompt goes on stdin: `--allowedTools` takes every word after it as a tool
- [x] 1.2 Read each fixture through before it's added. Replace the temporary directory's path with a fixed
      placeholder if it names the owner's home. Verify with `grep` that neither holds `sk-ant`, `ghp_`, `gho_`,
      `ghs_`, `TOKEN=` or the home directory's path. Done: no key or token in the raw captures, but the init
      messages listed the owner's local setup, so those lists were emptied and the rate-limit event dropped (design
      D3). The grep, with `martin`, `/Users/`, `claude-troupe`, `private/tmp` and `hps` added, finds 0 in each

## 2. The report step (design D1 to D3)

- [x] 2.1 In `test_claude_review_workflow.py`, replace "only the action runs" with D3's rule: the only `run` step is
      the one named for reporting denials, with exactly D1's `shell`, `if`, `continue-on-error` and `env`, after the
      action, whose step has `id: review`, and with a script whose sha256 matches the test's constant. Add
      parametrised mutations for each: another `run` step, a changed script, the step moved before the action, a
      missing `continue-on-error`, the path interpolated into the script, `display_report` given to the action.
      Add behaviour tests that take the script from the workflow and run it with `sys.executable`: the denied fixture
      prints one `::warning` line naming `WebFetch` and its URL; the clean one prints `No tool call was refused.`
      and no `::`; no `EXECUTION_FILE`, or no file, gives a warning that the denials are unknown and exit 0; a file
      that isn't JSON, a JSON object, or a list with no `result` message gives a warning naming the problem and exit 1;
      a `tool_input` holding `\n::error::x`, `%0A` and 1,000 characters prints one line, escaped, cut to 300
      characters before escaping. Verify the new tests fail against the current workflow, for the reason they name
- [x] 2.2 Add the step and `id: review` to `.github/workflows/claude-review.yml`, with a comment naming this design
      and why the session's output stays hidden. Verify `uv run pytest scripts/tests/test_claude_review_workflow.py`
      passes, every parametrised mutation is named, and the behaviour tests pass. Done: 88 passed locally; CI's
      `check` job runs them on Linux, where the step runs (the OS legs run only `test_guard_*.py`; design D3)
- [x] 2.3 Say in `docs/development-workflow.md`'s review paragraph and README.md's row that a refused tool call is named
      in the run's log, and nothing else of the session is. Verify `uv run scripts/check.py` passes

## 3. The guide's checkout (design D4)

- [x] 3.1 In the test, require exactly two checkouts: the pull request's own (no `repository`), and
      `troupe-run/.github` with exactly D4's inputs, after it. Both keep `persist-credentials: false`. Add mutations:
      the guide's checkout keeps credentials, has another `repository`, a `path` outside the workspace
      (`../guide`, `/tmp/guide`), or comes before the main checkout; a third checkout; `WebFetch` added to the tools.
      Add a test that the prompt names `.org-guide/CONTRIBUTING.md` and `org-profile/CONTRIBUTING.md` and no longer
      holds the guide's URL. Verify these fail against the current workflow, for the reason they name
- [x] 3.2 Add the checkout and rewrite check 5 of the prompt as D4 says. Verify the tests from 3.1 pass, and
      `uv run scripts/check.py` passes

## 4. Before delivery

- [x] 4.1 Run troupe's `uv run scripts/check.py` and website's `npx vitest run tests/unit/workflow-node-version.test.ts`,
      each in a worktree of its repository with the new `claude-review.yml` in place (claude-pr-review D6). Verify both
      pass, and record the commands and results here. Done (2026-10-26, e412dc8's workflow, in scratch clones rather
      than worktrees, as claude-pr-review did): website at e2af256, `workflow-node-version.test.ts` 8 passed; troupe at
      2d24fcf, `scripts/check.py` all gates passed (2822 passed, 14 skipped)
- [ ] 4.2 On this change's pull request, read its `claude review` run (design Migration Plan, step 1). Verify that the
      guide's checkout step holds `.org-guide/CONTRIBUTING.md`, that the review's summary cites the guide, that the
      report step printed `No tool call was refused.` or one warning per denial matching `permission_denials_count`,
      that it shows no other session output, and that the review's comments are by `troupe-run-review[bot]`. Record
      the run ID and what each check showed
- [x] 4.3 Run `tofu.py plan` against current state (fast-forward onto `origin/main` first). Verify it shows exactly
      `.github/workflows/claude-review.yml` changing in troupe and in website, and nothing else. Done (2026-10-26,
      rebased onto acb1af3, after the relabel's apply): 0 to add, 2 to change, 0 to destroy, both
      `github_repository_file.guard["<repo>:.github/workflows/claude-review.yml"]`, sha `b2e1cc30b8fb` → `b115174636c1`

## Workflow follow-up

- Archive on the branch before merging (`/opsx:archive`), and run `openspec validate pr-review --type spec --strict`
  on the synced main spec.
- After the merge: the owner approves the apply. Check that `.github/workflows/claude-review.yml` in troupe and website
  matches the source (sha256), and that each delivery commit's checks pass.
- Comment on #161 with the PR and the archived change, close it if the PR didn't, and set its card to Done.
- #159 stays open. Its first reviews in troupe and website check this version. Its denial item is done when they each
  print `No tool call was refused.`, or any denial they name is explained there (owner, 2026-10-26). #157's denial
  itself can't be recovered, and the guide's checkout may remove its likeliest cause, so it may never be named.
