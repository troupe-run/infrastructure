# Tasks

## 1. Probe (design D1)

- [x] 1.1 Create public `troupe-run/infra-probe-review-check` with `gh repo create` on its own, and push a copy of
  `claude-review.yml` in which the review job's Claude step is a stub (`sleep "$SLEEP"; exit "$EXIT"`, both read from
  a file on the branch, so a push sets them) and no step uses a secret, plus the new `claude review completed` job as
  D2 and D3 describe it, with D4 as a plain "print what it would carry forward" step. Add a ruleset on `main`
  requiring `claude review completed` from `github-actions`. Verify the workflow is on the probe's `main` and
  `gh api repos/troupe-run/infra-probe-review-check/rules/branches/main` lists the required check
- [x] 1.2 Open a pull request; let its review succeed. Record the check on the head, then push with the stub sleeping
  120 seconds and post an inline comment as the owner on it, and reply to it, while it sleeps. Record for the reply's
  run: its `head_sha` in `gh api .../actions/runs/<id>`, and which commit its check runs land on
  (`gh api .../commits/<head>/check-runs`). Verify by those two reads
- [x] 1.3 With a review sleeping (its `claude review completed` queued behind it), start a second run on the same
  head whose check fails at once; let the sleeping run then succeed. Record which check the ruleset counts
  (`gh pr view <n> --json mergeStateStatus,statusCheckRollup`, and whether `gh pr merge --rebase` is refused). Repeat
  with the order reversed. Verify by the reads after each
- [x] 1.4 Cancel the last review (`gh run cancel`), record that the check fails and the merge is refused; then
  `gh run rerun <id>` and record that the re-run's check counts and the merge is allowed (don't merge: close the pull
  request afterwards). Verify by the reads
- [x] 1.5 Add `merge_group:` and turn the probe's merge queue on; record that the check reports as skipped on the
  group's commit and the queue lands the pull request. Verify with the group's check runs and `main`'s log
- [x] 1.6 Write what 1.2 to 1.5 showed into design.md's "Probe results", and settle D4's two branches (reply runs on
  the head or not; fail or wait while a review is running), editing D4 and the pr-review delta if a branch is dropped.
  Delete the probe with `gh repo delete troupe-run/infra-probe-review-check --yes`; verify `gh repo view` says it's
  gone

## 2. The job (design D2, D3, D5)

- [ ] 2.1 Add `merge_group:` to `claude-review.yml`'s triggers with a comment naming D5, and the `completed` job
  (`claude review completed`): `needs: [gate, review, resolve]`, `if: always() && github.event_name == 'pull_request'`,
  `permissions: {}`, a short timeout, no checkout, no secret, and an inline Python step
  that reads the needs' results and the event from `env:`. Update the file's header comment ("It isn't a required
  check" no longer holds). Verify `uv run scripts/check.py` passes
- [ ] 2.2 Implement D3's steps 1 to 3 in the step, each failure an escaped `::error` with `gh run rerun <id>`; pin the
  job's shape in `scripts/tests/test_claude_review_workflow.py`'s `problems()` and add named cases to
  `test_each_way_the_workflow_can_go_wrong_is_named` (missing `always()`, running on a merge group, a secret, a
  checkout, a permission, joining the concurrency group). Add tests that run the step for a bot's, a fork's, a completed, a failed,
  a cancelled review and a failed gate, each named for its outcome. Verify `uv run pytest
  scripts/tests/test_claude_review_workflow.py` passes
- [ ] 2.3 Pin D4 as task 1.6 settled it: the job runs for pull request events only. Add named cases to
  `test_each_way_the_workflow_can_go_wrong_is_named` for an `if:` that also lets a comment's event or every event
  through, and say in the job's comment why (Probe results 1 and 2). Verify the tests pass, and fail with the `if:`
  widened to `always()`

## 3. Required checks and delivery (design D6)

- [ ] 3.1 Add `claude review completed` (app `github-actions`) to troupe, infrastructure and website in
  `tofu/required-checks.json`, and to the required-checks tests' expected lists; verify `uv run scripts/check.py`
  passes and `tofu plan` (local, against fast-forwarded `main`) shows the three rulesets and the two deliveries of
  `claude-review.yml`, and nothing else
- [ ] 3.2 Run website's `npx vitest run tests/unit/workflow-node-version.test.ts` and troupe's `uv run scripts/check.py`
  with the new `claude-review.yml` in place in scratch clones, as the file's header asks; verify both pass

## 4. Docs (development-workflow delta)

- [ ] 4.1 In `docs/development-workflow.md`, next to "the review of the last push", say the required check holds the
  pull request until the review of its head completed, and that a cancelled or failed last review is re-run with
  `gh run rerun <id>` from the check's message; update "it isn't a required check" wherever the docs or CLAUDE.md say
  it of the review. Add a test that the doc names `claude review completed`; verify it passes and fails with the
  name removed

## Workflow follow-up

- Open the draft pull request (`Closes #242`), act on Claude's review, mark it ready; the owner approves `plan (pull
  request)`.
- Archive on the branch before merging.
- After the merge and the owner's apply, check on a real pull request in each repository that `claude review
  completed` reports, comment on open pull requests that need a push to get it, and comment on #242 with the PR and
  the archived change; check its card says Done.
