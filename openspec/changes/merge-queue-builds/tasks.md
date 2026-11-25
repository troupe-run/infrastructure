# Tasks

## 1. Check GitHub takes the values

- [ ] 1.1 On a throwaway public repository (`troupe-run/infra-probe-merge-queue-builds`), create a `main` ruleset with
      the module's merge queue and `max_entries_to_build` 2, `max_entries_to_merge` 5,
      `check_response_timeout_minutes` 120; read it back and confirm GitHub kept all three (D3). Delete the repository.

## 2. Per-repository limits

- [ ] 2.1 `tofu/modules/repository/variables.tf`: `merge_queue_builds` (default 5, 0–100) and
      `merge_queue_check_timeout_minutes` (default 60, 1–360), each validated (D1); `main.tf` uses them in the
      `merge_queue` block, with the comment saying who sets them. Verify: `tofu validate` passes, and refuses a
      temporary out-of-range value on troupe's call (reverted).
- [ ] 2.2 `tofu/repositories.tf`: troupe sets 2 and 120, with a comment naming infrastructure#409 (D2). Verify:
      `uv run scripts/check.py` passes.

## 3. Evidence

- [ ] 3.1 The PR's plan shows exactly one resource changing, troupe's `protect main` ruleset, with only
      `max_entries_to_build` 5 → 2 and `check_response_timeout_minutes` 60 → 120; infrastructure's and website's
      rulesets plan no change.
- [ ] 3.2 The PR body records D4's recommendation for infrastructure and website.

## Workflow follow-up

- Archive the change once Claude's review of the last push is clean.
- After the merge, the owner approves the `apply` job; then `gh api repos/troupe-run/troupe/rulesets/24895454` shows
  `max_entries_to_build` 2 and `check_response_timeout_minutes` 120. Comment on infrastructure#409 with the PR and the
  archived change.
