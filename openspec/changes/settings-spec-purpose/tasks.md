# Tasks

## 1. Record the Purpose

- [ ] 1.1 Read the `settings` Purpose from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/settings/spec.md`, through `scripts/oob.py`'s
      `purpose()`), and add it to `oob/troupe-spec-purposes.json` where design D1 says. Verify the file has 27
      entries, its keys are sorted (`jq -r 'keys_unsorted[]'` against `sort`), the new entry matches #228's quote,
      `git diff` shows only that one added line, and `uv run scripts/check.py` passes

## 2. Verify

- [ ] 2.1 Fast-forward the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports no
      differences, and keep its output for the pull request. If it reports a changed `settings` Purpose, update the
      record, check design D2 against the new text, and re-run 1.1's checks. Stop and revise the change if it reports
      anything else
- [ ] 2.2 Run `git diff --name-only origin/main...HEAD | python3 scripts/plan_needed.py` and verify it prints
      `plan=false`, so the pull request asks for no `plan-pr` approval (proposal, Impact)
- [ ] 2.3 Run `openspec validate settings-spec-purpose --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #228` and `oob.py`'s output from 2.1. Archive the change on the branch before
  merging.
- The owner merges by rebase, through the merge queue.
- After the merge, check the `tofu` run on `main`: `plan (main)` has no changes, `apply (main)` is skipped, and
  `drift (out of band)` passes. If a drift run that started before the merge failed, re-run its job (design, Risks).
- Check #228 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #228 with the pull request and the archived change.
