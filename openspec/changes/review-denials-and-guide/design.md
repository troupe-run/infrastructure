# Design

## Context

See proposal.md for why. What shapes the approach (read 2026-10-26):

- **The execution file.** `anthropics/claude-code-action` v1.0.262 writes every SDK message as a JSON array to
  `$RUNNER_TEMP/claude-execution-output.json` (`base-action/src/execution-file.ts`), and sets the action's
  `execution_file` output to that path. The `result` message carries `permission_denials`, a list of
  `{tool_name, tool_use_id, tool_input}`. The action prints only their count (`permission_denials_count`,
  `base-action/src/run-claude-sdk.ts`). The file is outside the checkout, so the review's own `Read(./**)` can't reach
  it.
- **What's been seen.** #157's run 40299015647 counted 1 denial, after D9 of claude-pr-review scoped Read, Grep and
  Glob. #160's run 40302806860, with the same workflow and prompt, counted 0. So the guide's URL doesn't always cause a
  denial, and the cause is still unknown.
- **The workflow's test** (`scripts/tests/test_claude_review_workflow.py`) refuses any `run` step ("only the action
  runs"), and refuses `show_full_output` and `display_report`. It requires `persist-credentials: false` on every
  checkout already.
- **The guide's source** is `org-profile/CONTRIBUTING.md` here. `tofu/org_profile.tf` writes it to troupe-run/.github,
  which is public, so its `main` holds what's applied.
- **Bot skip, seen.** troupe's release pull request #89 (by `troupe-run-release[bot]`) got run 40302116098 on
  2026-10-26: the `claude review` job was skipped and the run didn't fail. That's #159's third check, recorded there,
  not here.

## Goals / Non-Goals

**Goals:**
- The next denial anywhere is named in its run's log, with nothing else from the session shown.
- The review can read every document its prompt tells it to check.

**Non-Goals:**
- Finding the cause of run 40299015647's denial. Its execution file is gone with its runner. Its likeliest cause is the
  guide's URL (a local `claude -p` run asked to fetch it gave one `WebFetch` denial), which D4 removes, so it may never
  recur to be named. #159's denial item is done when the first reviews in troupe and website each print
  `No tool call was refused.`, or any denial they name is explained there (owner, 2026-10-26).
- Failing a review on a denial. The review is advisory. A denial is a thing to look into, not a broken run.
- Giving the review a URL fetch, `gh api`, or any other tool.

## Decisions

### D1. A report step that reads only the denials

A step after the action, with `continue-on-error: true` and `if: ${{ !cancelled() }}`, runs a short Python script
(`shell: python`, standard library only). It gets the file's path through `env: EXECUTION_FILE:
${{ steps.review.outputs.execution_file }}`, never interpolated into the script, so the action step gains
`id: review`.

- It reads the file, takes `permission_denials` from every message whose `type` is `result`, and for each one prints
  `::warning title=Claude was refused a tool call::<tool_name> <tool_input>`. `tool_input` is dumped as JSON with sorted
  keys, cut to 300 characters.
- With no denial it prints `No tool call was refused.` as a plain line.
- **Absent and malformed aren't the same.** No path, or no file (the action failed before writing it) → a warning that
  the denials are unknown, and exit 0. A file that isn't JSON, isn't a list, or has no `result` message → a warning
  naming the problem, and exit 1. `continue-on-error` keeps the job green, and the step shows as failed, so it isn't
  read as "nothing refused".
- **Alternatives rejected (owner, 2026-10-26):** `show_full_output`, which shows the whole session, which is what the
  action hides for security. Uploading the execution file as an artifact, which on a public repository lets anyone
  logged in download the whole transcript. No report at all, which leaves the cause to be guessed.

### D2. A denied input can't start a workflow command

A denied call's input can be text a pull request put there, for example a command it asked Claude to run. The runner
reads workflow commands from any line of a step's output that starts with `::`. So the script escapes the message as
the runner's toolkit does: `%` → `%25`, `\r` → `%0D`, `\n` → `%0A`. Then the whole report is one line per denial, each
starting with the script's own `::warning`, and nothing from the input can begin a line. The input is cut to length
before it's escaped, so an escape is never split, and `::` inside a message is just text. A secret can't appear in it unless Claude
read one, which D9 of claude-pr-review stops. Secrets the job holds are masked in the log anyway.

### D3. The test pins the report step exactly

"Only the action runs" becomes "the only `run` step is the report step". The test finds it by name, and checks its
`shell`, `if`, `continue-on-error` and `env` against constants. It checks the script against a sha256 written in the
test, so a change to the script changes the test in the same diff, which the owner reviews. Any other `run` step is
still named and refused. Behaviour tests run the script itself, taken from the workflow, with `sys.executable`. They run in
CI's Linux `check` job: the OS legs run only `test_guard_*.py`, and the step itself runs only on `ubuntu-latest`.
(This design first said all three OSes, which CI doesn't do for this file; corrected in apply, 2026-10-26.)

The fixtures are real execution files, not hand-written ones. They're captured locally with
`claude -p --output-format stream-json --verbose --setting-sources user --allowedTools Read(./**)`, in an empty
directory, the same message stream the action collects. Each one is turned into a JSON array, as the action writes it.
One run is asked to fetch a URL, so it's refused. The other is asked to read a file in the directory. Each fixture is
read through before it's committed. The raw captures held no environment, key or token, but their `init` and
`commands_changed` messages listed the owner's local setup (MCP servers, plugins, skills, memory paths), and a
`rate_limit_event` showed the account's usage. So those lists are emptied, that event is dropped, and the scratch
directory's path becomes `/home/runner/work/probe/probe`. Every other message, the `result` included, is as captured
(2026-10-26, Claude Code 2.1.310). The script reads only `result` messages, so nothing it reads was changed. The escaping test changes a real fixture's `tool_input` to hold `::`, `%` and newlines.

### D4. The guide comes from a second, sparse checkout

A second `actions/checkout` of `troupe-run/.github` at `ref: main`, `path: .org-guide`, `sparse-checkout:
CONTRIBUTING.md` with `sparse-checkout-cone-mode: false`, `fetch-depth: 1`, `persist-credentials: false`. It runs
after the main checkout, which would otherwise clean the workspace. It uses the job's own `contents: read` token,
which can read a public repository. The App token isn't involved.

- Check 5 of the prompt names `.org-guide/CONTRIBUTING.md`, read with Read. In infrastructure, the prompt adds that
  `org-profile/CONTRIBUTING.md` is the guide's source: if the pull request changes it, check the pull request against
  its own version. The prompt is the same in every repository, so it says this with "if the repository has
  `org-profile/CONTRIBUTING.md`".
- `.org-guide` is a path no repository uses. A pull request that adds one gets it replaced by the checkout.
- The test requires exactly two checkouts: one with no `repository` (the pull request's own), and one with exactly the
  inputs above. Both need `persist-credentials: false`.
- **Alternatives rejected (owner, 2026-10-26):** dropping check 5, which loses the org's rules where a repository's
  `CLAUDE.md` only summarises them. Allowing `gh api`, which widens the tools and can write with the App token.

## Risks / Trade-offs

- [A denied input still shows in a public log] → it's cut to 300 characters, escaped, and holds only what Claude tried
  to do. The session's messages and tool results stay hidden.
- [The action changes the execution file's shape in a new release] → the script refuses a shape it doesn't know
  (D1's exit 1), and the fixtures pin the current shape. A Dependabot bump to the action runs this repository's tests
  on its pull request.
- [A sparse, non-cone checkout behaves differently than expected, for example checking out the whole repository] →
  this change's own pull request run shows which files `.org-guide` holds (task 4.2). The whole of troupe-run/.github
  is public and holds nothing secret, so the worst case is a few more files in the workspace.
- [`Read(./**)` doesn't reach a dot-directory] → task 4.2 checks that the review read the guide and that no call
  was refused.

## Migration Plan

1. This change's pull request runs the new workflow in infrastructure (a `pull_request` run uses the head's copy).
   Check the guide's checkout, the report step's line or warnings, and the review's comments.
2. Before delivery, run troupe's `uv run scripts/check.py` and website's
   `npx vitest run tests/unit/workflow-node-version.test.ts` with the new file in place (claude-pr-review D6).
3. After the merge, the owner approves the apply, which updates `.github/workflows/claude-review.yml` in **troupe and
   website** (2 changes). Check that both copies match the source.
4. #159 takes it from there: its first reviews in troupe and website run this version.

Rollback: revert the commit. The next apply delivers the earlier workflow again. Nothing else holds state.
