# Tasks

Groups 1 to 4 need nothing from the owner. Group 5 needs a throwaway repository, which the guard lets an agent create
under `troupe-run/infra-probe-*`. The board job's proof needs the apply and the owner's secret, so it follows the
merge (Workflow follow-up).

## 1. The `board` environment on infrastructure (spec: board-credentials; design D5)

- [x] 1.1 Key `MAIN_ONLY` in `scripts/tests/test_main_only_environments.py` by `(repository module, environment)`,
      keeping every existing entry, test name and message, and add `("repo_infrastructure", "board")`. Verify the
      existing tests still pass on the old entries, and that the suite fails naming infrastructure's `board` as not
      declared, before 1.2
- [x] 1.2 In `tofu/board.tf`, declare the `board` environment on `module.repo_infrastructure` with its `main`-only
      deployment policy and `BOARD_APP_CLIENT_ID` from the same `local.board_app_client_id`, and update the file's
      header comment to name both repositories and #60. Verify the test from 1.1 passes and `uv run scripts/check.py`
      passes (tofu fmt, validate)
- [x] 1.3 Add a test that a deleted infrastructure `board` declaration is named, next to
      `test_a_deleted_board_declaration_is_named`. Verify it fails on a scratch copy with the block removed, naming
      the repository and environment, then passes on the real file

## 2. The declaration and the logic (spec: schedule-watch; design D2 to D4, D8)

- [x] 2.1 Save real API payloads as fixtures under `scripts/tests/fixtures/schedule-watch/`: website's
      `links-weekly.yml` workflow, its `runs?event=schedule&per_page=1` page, an empty runs page (from a workflow with
      no scheduled runs) and a 404 body, each read with `gh api` and trimmed only of fields the script doesn't read.
      Verify each file's source command is recorded in a README in that directory
- [x] 2.2 Write the tests first, in `scripts/tests/test_watch_schedules.py`, one per spec scenario that's decidable
      offline: declaration parsing (website's entry is there; a malformed or unknown field is refused, naming the entry
      and field), the four problem kinds, a manual run not counting, errors other than 404 raising rather than
      reporting, the issue-action table in design D4 (open, nothing, comment, close, nothing), the fingerprint
      ignoring ages, the oldest of two tracking issues chosen, a person's issue with the same title ignored, and the
      `extra-workflow` check refusing values outside `troupe-run/<repository>/<file>.yml`. Verify they fail because
      the script doesn't exist yet
- [x] 2.3 Add `scripts/watched-schedules.json` with website's `links-weekly.yml` at 8 days, and
      `scripts/watch_schedules.py` (standard library; pure functions plus a `gh` layer; prints only when
      `GITHUB_ACTIONS` is unset; writes `issue-url` to `GITHUB_OUTPUT` only when it opened or commented; exits non-zero
      after updating the issue when it found a problem). Verify the tests from 2.2 pass and `uv run scripts/check.py`
      passes (ruff, mypy --strict)
- [x] 2.4 Run `uv run scripts/watch_schedules.py` locally with the owner's `gh` login. Verify it prints website's
      `links-weekly.yml` as fine, says it would take no action, and changes nothing on GitHub (no new issue, comment
      or closure on infrastructure)
- [x] 2.5 Decide the declaration's check scope: add `scripts/watched-schedules.json` to `scripts/check-paths.toml`
      with the tests tagged for it, or leave it in no group (full check). Verify `uv run scripts/check.py` passes and
      the guard's `check-scope` names the chosen scope for a change to that file

## 3. The workflow (spec: schedule-watch; design D1, D5 to D7)

- [x] 3.1 Write `scripts/tests/test_schedules_workflow.py` first, as `test_oob_job.py` does for the drift job: the
      triggers are a daily schedule and `workflow_dispatch` with `extra-workflow` only (no `pull_request`, no `push`);
      top-level `permissions: {}`; the watch job has exactly `contents: read` and `issues: write`, no environment and
      `GH_TOKEN: ${{ github.token }}`; the board job needs the watch job, runs on `!cancelled()` and a non-empty
      `issue-url`, has environment `board` and `permissions: {}`, checks out nothing, checks the URL against
      infrastructure's issue pattern, and mints a token with only `permission-organization-projects: write`. Each
      way it can go wrong is named, as in `test_each_way_the_job_can_go_wrong_is_named`. Verify they fail because the
      file doesn't exist
- [x] 3.2 Write `.github/workflows/schedules.yml` (cron `0 12 * * *`), with a header comment naming the spec, #60 and
      the 60-day pause, in the style of `tofu.yml`. Verify the tests from 3.1 pass and `uv run scripts/check.py`
      passes
- [x] 3.3 Check the board job's URL guard as a shell snippet: run its `[[ =~ ]]` test locally against
      `https://github.com/troupe-run/infrastructure/issues/12` (accepted), and website's issue URL, `…/pull/12`,
      `…/issues/12/x` and an empty string (each refused). Verify the outputs

## 4. Documentation

- [ ] 4.1 README.md: a layout row for `schedules.yml`, `watch_schedules.py` and `watched-schedules.json`, and in
      "Running a plan", a sentence that the watch reports website's check stopping, and that it stops too if this
      repository goes 60 days without activity. Verify `uv run scripts/check.py` passes (the docs tests)
- [ ] 4.2 oob/README.md: in the board App's section, the command to set `BOARD_APP_PRIVATE_KEY` on infrastructure's
      `board` environment and to check it by name, beside website's. Verify the check command runs as written
      (it returns 404 for the environment until the apply, which is expected)

## 5. Prove the watch job on a throwaway repository (design D6, D7)

- [ ] 5.1 Create `troupe-run/infra-probe-schedule-watch` (public), push to it the script, the declaration, and a copy
      of `schedules.yml` without the board job, plus a scheduled workflow `probe.yml`, and turn `probe.yml` off with
      `gh workflow disable`. Verify `gh workflow list -R troupe-run/infra-probe-schedule-watch --all` shows `probe.yml`
      disabled
- [ ] 5.2 Run the probe's watch by hand without input. Verify, from its log, that it read website's
      `links-weekly.yml` with `GITHUB_TOKEN` and found it fine, and record in design D6 whether the installation token
      read another repository's Actions API. If it was refused, switch to the drift check's read-only App token, update
      D6 and group 3, and run again
- [ ] 5.3 Run it with `extra-workflow=troupe-run/infra-probe-schedule-watch/probe.yml`. Verify the run failed, the
      tracking issue opened in the probe repository naming `not-active`/`disabled_manually` and the fix, and
      `issue-url` was set. Run it again with the same input: verify no new comment. Run it once more without input:
      verify the issue is closed with a comment linking the run
- [ ] 5.4 Run it with `extra-workflow=someone-else/repo/x.yml`. Verify the run fails naming the value, and the probe
      repository has no new issue or comment
- [ ] 5.5 Delete the probe repository. Verify `gh repo view troupe-run/infra-probe-schedule-watch` fails with not
      found

## 6. The plan

- [ ] 6.1 Open the pull request (`Closes #60`) and get CI's plan. Verify it creates only the `board` environment, its
      deployment policy and `BOARD_APP_CLIENT_ID` on infrastructure, changes no ruleset and touches no secret
- [ ] 6.2 Verify `openspec validate watch-website-link-check --strict` passes

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`).
- After the merge and CI's apply (these can't be ticked before archive, so they're not tracked tasks):
  - Owner: set the secret with
    `op read -n "op://troupe.run/troupe-run-board/private key" | gh secret set BOARD_APP_PRIVATE_KEY --env board -R troupe-run/infrastructure`,
    and check it by name: `gh api repos/troupe-run/infrastructure/environments/board/secrets --jq '.secrets[].name'`
    prints `BOARD_APP_PRIVATE_KEY`.
  - Prove the board job (design Migration Plan, step 3): a throwaway repository with a disabled scheduled workflow,
    `gh workflow run schedules.yml -R troupe-run/infrastructure -f extra-workflow=troupe-run/infra-probe-<name>/<file>`,
    then check the tracking issue opened and its card is on the troupe roadmap board
    (`gh issue view <n> -R troupe-run/infrastructure --json projectItems`). Run again without input to close it, and
    delete the throwaway repository.
  - Decide whether to raise a website issue for the reverse watch (proposal, "Not in this change"); if raised, it goes
    on the board.
- After the merge, comment on #60 with the PR and the archived change, and check the card says Done.
