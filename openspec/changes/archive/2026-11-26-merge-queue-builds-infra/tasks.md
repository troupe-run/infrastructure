# Tasks

## 1. infrastructure's limits

- [x] 1.1 `tofu/repositories.tf`: infrastructure's module call sets `merge_queue_builds = 2` and
      `merge_queue_check_timeout_minutes = 120`, with a comment naming #413 (D1, D2). Verify: `tofu validate` and
      `uv run scripts/check.py` pass (the commit hook's check).
- [x] 1.2 The PR body carries #413's numbers and links #414.

## Workflow follow-up

- Archive the change before the PR is marked ready, so the owner approves the plan once, on the final head.
- Before the merge, the PR's plan shows exactly one resource changing, infrastructure's `protect main` ruleset, with
  only `max_entries_to_build` 5 → 2 and `check_response_timeout_minutes` 60 → 120.
- After the apply, `gh api repos/troupe-run/infrastructure/rulesets` shows those values on `protect main`. Comment on
  #413 with the PR and the archived change.
