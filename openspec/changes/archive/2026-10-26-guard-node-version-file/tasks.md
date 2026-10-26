# Tasks

## 1. Pin the failure before the fix

- [x] 1.1 Re-confirm D1's premise on the branch's `scripts/guard.py` (checked before apply, 2026-10-26; this catches
  a later change to `main`): the `ci` path reads the working tree only under `openspec/`, and never reads
  `git status` or untracked files. Verify by reading `run_ci_entry` and what it calls, and note the result here.
  Result: `scripts/guard.py` is identical to `origin/main` (e45f7ed), which is what D1 was checked against. Its only
  `status` strings are `gh` subcommands (`pr status`, `issue status`, `auth status`), and it has no `--porcelain`,
  `--others` or untracked-file read
- [x] 1.2 Run website's `tests/unit/workflow-node-version.test.ts`, unchanged, against this branch's current
  `guard.yml`. Copy website's `.github/workflows/` into a scratch directory, put this repository's `guard.yml` in it,
  and run website's vitest on that test with the scratch directory as the working directory. Verify it fails with
  exactly #155's two messages (`must have node-version-file: .nvmrc`, `must not have node-version (found
  "22.23.4")`), and record the command here for 3.1. Result: with website at `origin/main` (f9fe63e, its test and
  workflows unchanged), `cd <scratch> && <website>/node_modules/.bin/vitest run --root <website>
  tests/unit/workflow-node-version.test.ts` fails 1 of 8, with exactly those two messages for `guard.yml`, job
  "guard", step 3
- [x] 1.3 Add `scripts/tests/test_guard_workflow.py` (design D3): the website-rule check on `guard.yml`, naming each
  problem's job and step and ignoring `if:`, plus fixture cases (a pinned `setup-node`, a `setup-node` behind `if:`,
  a `node-version` input on another step) that it refuses. Verify the fixture cases pass and the `guard.yml` case
  **fails** on the unchanged workflow with the same two problems as 1.2, and commit it marked
  `xfail(strict=True, reason="#155")`

## 2. Take Node from .nvmrc (design D1, D2)

- [x] 2.1 In `.github/workflows/guard.yml`, add `NODE_VERSION: 22.23.4` to the job's `env` with D2's comment, add
  the "Choose the Node version" step before `setup-node`, and change `setup-node` to `node-version-file: .nvmrc`.
  Update the file's header comment if it describes the steps. Verify by removing 1.3's `xfail` mark: the test passes
- [x] 2.2 Add to `test_guard_workflow.py`: the choosing step comes before the first `setup-node` step; run with bash
  in a temporary directory, it writes `NODE_VERSION` and a newline when there's no `.nvmrc`, and leaves an existing
  `.nvmrc` byte for byte unchanged. Skip the run cases where bash isn't found. Verify they pass, and that the
  "unchanged" case fails if the step's `-e` test is removed (check by hand, then restore)
- [x] 2.3 In `docs/development-workflow.md`, "Where the guard comes from" (next to "Moving the OpenSpec version"),
  say that the `guard` check's Node comes from the repository's `.nvmrc`, or from `NODE_VERSION` in `guard.yml` where
  there's none, and that the workflow never names a Node version as a step input, because website's test refuses one
  (troupe-run/website#4). Verify `uv run pytest scripts/tests/test_guard_docs.py` passes, and `uv run
  scripts/check.py` passes (workflow lint included)

## 3. Integration checks

- [x] 3.1 Rerun 1.2's command against the new `guard.yml`. Verify website's test passes unchanged, and record both
  results (old fails, new passes) in the pull request. Result: 8 of 8 pass on the new `guard.yml`, with website's test
  unchanged. website's own checkout still has the old `guard.yml`, so the run read the scratch copy
- [x] 3.2 Push the branch and open the pull request (`Closes #155`). Verify this repository's `guard` run on it
  passes and its log says `No .nvmrc here, so Node 22.23.4, the guard's pin`, and that the PR's plan comment shows
  only `guard.yml`'s content changing, for troupe and website. Result: PR #156. Both `guard` runs on 1d3f100 (push
  and pull request) pass and log that line, then download 22.23.4 from `node-version-file: .nvmrc`. The plan for
  1d3f100 is 0 to add, 2 to change, 0 to destroy: `github_repository_file.guard` for `.github/workflows/guard.yml`
  in troupe and website, content and commit message in place. No modes to set

## Workflow follow-up

- Archive the change on the branch before asking for the plan's approval, and rebase onto `main`'s state commit, so
  the approval is asked once.
- After the owner merges and approves the delivery's apply, verify on `main`: website's `guard` and CI runs pass,
  their `guard` log names Node from the repository's `.nvmrc`, and `uv run scripts/check.py` passes on a fresh
  website `main`. troupe's `guard` run on `main` passes and logs the pin.
- Comment on #155 with the PR and the archived change, check it's closed and its card says Done, and tell
  troupe-run/website#31 that its blocker is gone.
