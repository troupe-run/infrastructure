# Tasks

## 1. troupe's required checks

- [x] 1.1 Add the test from design D3 to `scripts/tests/test_required_checks.py`, named for what it checks (troupe
  requires `check` and no `check (` leg), and update the module docstring. Verify it fails on the current
  `tofu/required-checks.json`, naming the missing `check` and the 12 legs.
- [x] 1.2 Replace troupe's 12 legs in `tofu/required-checks.json` with `{"context": "check", "app": "github-actions"}`
  (design D1). Verify `uv run pytest scripts/tests/test_required_checks.py` passes, and that troupe's list is exactly
  `check`, `guard (workflow rules)` and `DCO`.
  - 2026-10-19: before the JSON change, `test_troupe_requires_its_check_result_and_none_of_its_legs` failed with
    `assert 'check' in {'check (macos-latest, Python 3.12)', ...}`. After it, the module's 20 tests pass, and troupe's
    list is `['check', 'guard (workflow rules)', 'DCO']`.
- [x] 1.3 Before relying on the name, read #117's latest head's check runs (`gh pr view 117 -R troupe-run/troupe
  --json statusCheckRollup`) and record here that `check` reports from GitHub Actions. If it doesn't, stop and revise
  the design.
  - 2026-10-19: #117's head `d47991d` has one `check` run, conclusion success, from app 15368 (`github-actions`).

## 2. Comments and docs

- [x] 2.1 Update `tofu/repositories.tf`'s comment and the README's rulesets section (design D4). Verify `git grep -n
  "Python 3.1[2-5])"` finds no troupe leg named as required outside archived changes.
  - 2026-10-19: the README's example is now `guard (workflow rules)` (job id `guard`), and the paragraph says troupe's
    twelve legs report through `check`. The grep, less archived changes and plan fixtures, finds only this change's
    own design and evidence.

## 3. Evidence

- [x] 3.1 Run `uv run scripts/check.py`; it passes. Record the result here.
  - 2026-10-19: all gates passed: ruff, mypy --strict, 1439 tests passed (14 skipped), tofu fmt, init and validate.
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
