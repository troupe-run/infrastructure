# Proposal

## Why

infrastructure#103 has collected four corrections since 2026-10-19. Two are stale wording: the docs still call #101 an
open question, and two comments claim as fact that commits keep a repository "active". The other two are guard bugs
found in use. `git commit -a` is refused for the very edit it would commit. A force-pushed branch's `guard` run judges
no commits, so its early warning says nothing. The owner chose to fix all four in one change (2026-10-25), though the
issue normally sends behaviour changes to their own issue.

## What Changes

- **`docs/development-workflow.md`, "Known gaps"**: the sentence about #101 says agents' own GitHub login was parked,
  because troupe decides actors' credentials (troupe-run/troupe#11). It no longer reads as an open decision.
- **`README.md` and `.github/workflows/schedules.yml`**: say that GitHub doesn't define the "activity" that keeps
  scheduled workflows on, and that commits (merges and the App's state commits) are *assumed* to count (#60, #105).
- **The pre-commit hook reads the index git is committing.** During `git commit -a` and `git commit <path>`, git
  names a temporary index in `GIT_INDEX_FILE`. Today every pre-commit read strips it and judges `.git/index`. This
  change extends to the pre-commit rules what `protocol-schema-commit-types` (D4) did for the commit-msg hook.
  `commit-checks` (the unstaged-changes test, the staged paths and the staged `scripts/check-paths.toml`),
  `unticked_archived_tasks` and `delivered_file_staged` then judge what the commit will contain. Today `git commit -a`
  with an unstaged tracked edit is refused for having that edit unstaged. After this change it goes ahead and runs
  the check.
- **A force-pushed branch's `guard` run judges its commits.** When a push payload's `before` isn't in the clone (the
  tip a force push replaced), the run takes its range from the merge-base with `origin/main`, as a first push already
  does. The run says it did so. Today it falls back to `--not --remotes`, which is empty for the pushed head, so every
  rule judges 0 commits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: two added requirements. The pre-commit rules judge what the commit being made contains,
  including with `git commit -a` and `git commit <path>`. The GitHub check on a push judges the branch's commits even
  when the push replaced a tip the clone doesn't have.

## Impact

- `scripts/guard.py`: `run_pre_commit`, `commit_checks`, `ReadStaged`, `committing_paths` (shared), and
  `github_ci_inputs`. Tests go in `scripts/tests/test_guard_git_hooks.py`, `test_guard_commit_rules.py` and
  `test_guard_push_and_ci.py`.
- `docs/development-workflow.md`: the #101 gap. The `commit-checks`, `delivered-file` and archived-tasks rows say
  `git commit -a` and `git commit <path>` are judged on what they commit. Where the docs say the `guard` check runs on a push, they say how a force push is judged.
- `README.md` and `.github/workflows/schedules.yml`: wording only.
- **Delivery**: `scripts/guard.py` is a delivered file. After merge, the owner-approved apply delivers it to
  **troupe and website** (`guard_targets`), so the plan shows it updated in place in both. Nothing else is delivered.
  website's `scripts/check-paths.toml` is unaffected.
- No OpenTofu resource changes. No GitHub settings change.
