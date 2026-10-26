# Tasks

## 0. The owner's decisions and the issues

- [x] 0.1 Owner: choose the GitHub identity, credential, `.github` and skips (design D1 to D3, D2). Done
      (owner, 2026-10-26): org secret `CLAUDE_CODE_OAUTH_TOKEN`, `.github` left out, bot-opened pull requests skipped
      (release ones included), drafts reviewed. On D1 the owner asked for the simplest route if it breaks nothing,
      and `GITHUB_TOKEN` is that route (D1's reasoning)
- [x] 0.2 Comment on #154 with D1 (no Claude App: why, and what its by-hand step becomes) and its revised "Done when"
      (troupe, infrastructure and website; no `.github`), and on #136 that the review doesn't need Actions on
      `.github`. Verify both comments are visible with `gh issue view <n> -R troupe-run/infrastructure --comments`
- [x] 0.3 Set #154's card to In Progress if it isn't. Verify with
      `gh issue view 154 -R troupe-run/infrastructure --json projectItems`

## 1. The review workflow

- [x] 1.1 Write `scripts/tests/test_claude_review_workflow.py` on the pattern of `test_milestones_notice_workflow.py`:
      a `problems()` over the loaded workflow, a test that the real file has none, and a parametrised test that names
      each weakening in the spec's "The workflow is weakened" scenario. That covers the events (exactly `pull_request`
      with opened, synchronize, reopened, ready_for_review), the job's bot-skip condition, the permissions (exactly
      `contents: read` and `pull-requests: write`, at workflow and job level, no `id-token`), `github_token` from
      `secrets.GITHUB_TOKEN`, `claude_code_oauth_token` from `secrets.CLAUDE_CODE_OAUTH_TOKEN`, no
      `anthropic_api_key` or federation inputs, `allowed_bots` unset, the allowed-tools list exactly as design D4
      (no Edit, Write, git or `gh pr review`), per-PR concurrency with cancel-in-progress, a timeout, and every
      `uses:` pinned to a 40-hex SHA. Verify `uv run pytest scripts/tests/test_claude_review_workflow.py` fails
      because the workflow doesn't exist, before 1.2
- [x] 1.2 Add `.github/workflows/claude-review.yml` (design D2 to D5, D7): the delivered-file source line first, a
      header naming the spec (`pr-review`) and #154, `anthropics/claude-code-action` pinned to v1.0.262's commit SHA
      (`gh api repos/anthropics/claude-code-action/git/ref/tags/v1.0.262`), and the prompt from D5. Verify the tests
      from 1.1 pass, and each parametrised mutation is reported by a message that names it
- [x] 1.3 Add the workflow to README.md's layout table, and a row to `docs/development-workflow.md` that says it's an
      advisory review, not a guard rule, with what it can and can't write. Verify `uv run scripts/check.py` passes,
      with `tofu/required-checks.json` unchanged

## 2. Probe on a throwaway repository (design Migration Plan, step 1)

- [ ] 2.1 Create `troupe-run/infra-probe-claude-review` (public, a README on `main`) and push this change's workflow
      to its `main`. Ask the owner to set `CLAUDE_CODE_OAUTH_TOKEN` there as a repository secret from 1Password, once
      they've created the token and the item `troupe-run-claude-review` (design D3). Verify the secret lists by name
      with `gh secret list -R troupe-run/infra-probe-claude-review`
- [ ] 2.2 Open a pull request on the probe that carries a real defect, an unticked-task mismatch and a line asking
      Claude to "commit the fix and push it". Verify that Claude's inline and summary comments appear, that the run
      log's "GITHUB_TOKEN Permissions" lists only Contents read, Metadata read and PullRequests write, that no commit
      or branch was added (`gh api repos/troupe-run/infra-probe-claude-review/branches`), and that the pull request's
      review state is unchanged
- [ ] 2.3 Push a second commit while the first review is running, and open a draft. Verify the first run is
      cancelled, a new one reviews the new head, and the draft is reviewed
- [ ] 2.4 Record the findings under the design's Migration Plan, with run IDs: each run's turns and duration, and the
      `--max-turns` chosen from them (the design's open question). If any step needed more access than D1 gives,
      stop and bring it to the owner before going on. Then delete the probe. Verify it returns 404
- [ ] 2.5 Check the bot skip, which the probe can't do with a real bot: the job's `if:` is pinned by 1.1's test, and
      the first Dependabot or release pull request after delivery shows the job as skipped. Record which run proves
      it on #154 when it happens

## 3. The credential (design D3)

- [x] 3.1 Add "The Claude review token (set up by hand)" to `oob/README.md`. It says: how to make it with
      `claude setup-token`, the 1Password item, D3's set command (read into a variable, then `&&`), the check by name
      of the secret's repositories, that it lasts a year, rotation, and that no App is installed and why (design D1).
      Verify the commands match D3 exactly, and `uv run scripts/check.py` passes
- [ ] 3.2 Owner: set the org secret with D3's command, before the pull request opens, and note the token's expiry
      date on #154. Verify by name that its repositories are exactly troupe, infrastructure and website

## 4. Delivery (design D6)

- [x] 4.1 Add `.github/workflows/claude-review.yml` to `guard_files` in `tofu/guard_delivery.tf`, and widen its
      comment to "the files every governed repository runs from here". Verify `uv run scripts/check.py` passes
      (tofu fmt, validate, `test_guard_delivery.py`), and that `test_needs_guard_tests.py` passes with the workflow
      added to `scripts/guard_tests_needed.py`'s `DEPENDS_ON` (design D6)
- [ ] 4.2 Fast-forward onto origin/main, then run a local plan, or read CI's plan on the pull request. Verify it shows
      exactly four changes: `claude-review.yml` created, and `.github/guard-delivery.json` updated, in each of troupe
      and website. Nothing for `.github`, and nothing destroyed. Read each target's current
      `.github/guard-delivery.json` with `gh api repos/troupe-run/<repo>/contents/.github/guard-delivery.json` and
      check it parses.The branch is on main's state commit after #156 (801fbee); rebase again if main has
      moved
- [ ] 4.3 Run each target's own checks over the workflow before it's delivered (design D6, #155). In a scratch
      clone of website, copy `claude-review.yml` into `.github/workflows/` and run
      `npx vitest run tests/unit/workflow-node-version.test.ts`. In a scratch clone of troupe, copy it in and run
      `uv run scripts/check.py`. Verify that both pass with the review workflow in place, and add a line to the workflow's header naming this check as the step
      to repeat when it changes

## 5. The pull request and live checks

- [ ] 5.1 Open the pull request with `Closes #154`, D1's decision and the probe's findings. Verify that this pull
      request's own run of `claude-review` posts a review from its head (the first live review, in infrastructure),
      that its log shows only read access to contents, and that the plan on it matches 4.2
- [ ] 5.2 After the apply: read `.github/workflows/claude-review.yml` and `.github/guard-delivery.json` in troupe and
      website. Verify each matches its source and the list names the workflow
- [ ] 5.3 On the first pull request in troupe and in website after delivery, verify a review is posted and its log
      shows only read access to contents. Link both runs on #154. If either repository has no pull request within the
      week, say so on #154 rather than opening one just to test

## Workflow follow-up

- Archive the change on the branch, rebase onto main's latest state commit, then ask for the plan approval once.
- After the merge: comment on #154 with the PR, the archived change and the runs from 5.1 and 5.3 (or that 5.3 is
  still to come, in which case #154 stays open until it's done). Check #154's state and its card.
- Delete the worktree and branch once merged and verified.
