# Tasks

## 1. troupe's required checks

- [ ] 1.1 Add the test from design D3 to `scripts/tests/test_required_checks.py`, named for what it checks (troupe
  requires `check` and no `check (` leg), and update the module docstring. Verify it fails on the current
  `tofu/required-checks.json`, naming the missing `check` and the 12 legs.
- [ ] 1.2 Replace troupe's 12 legs in `tofu/required-checks.json` with `{"context": "check", "app": "github-actions"}`
  (design D1). Verify `uv run pytest scripts/tests/test_required_checks.py` passes, and that troupe's list is exactly
  `check`, `guard (workflow rules)` and `DCO`.
- [ ] 1.3 Before relying on the name, read #117's latest head's check runs (`gh pr view 117 -R troupe-run/troupe
  --json statusCheckRollup`) and record here that `check` reports from GitHub Actions. If it doesn't, stop and revise
  the design.

## 2. Comments and docs

- [ ] 2.1 Update `tofu/repositories.tf`'s comment and the README's rulesets section (design D4). Verify `git grep -n
  "Python 3.1[2-5])"` finds no troupe leg named as required outside archived changes.

## 3. Evidence

- [ ] 3.1 Run `uv run scripts/check.py`; it passes. Record the result here.
- [ ] 3.2 Open the pull request (`Closes #104`), saying in its body that it merges and is applied before
  troupe-run/troupe#117 (design D2). Once the owner approves the plan run, record here that the plan changes only
  troupe's "protect main" ruleset: 12 required checks removed, `check` (integration 15368) added, nothing else.

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase, once #117 is green and
  archived.
- After the merge, the owner approves main's apply. Verify troupe's ruleset requires exactly `check`, `guard (workflow
  rules)` and `DCO` (`gh api repos/troupe-run/troupe/rulesets/<id>`), then tell the `ci-check-scope` session #117 can
  merge.
- After #117 merges, verify a troupe pull request whose latest push skipped the legs shows as mergeable, and record it
  on #104.
- Comment on #104 with the pull request and the archived change. Check it's closed and its board card says Done.
- Remove this change's branch and worktree once it's merged and verified.
