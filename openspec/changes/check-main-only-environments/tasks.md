# Tasks

## 1. The check (D1 to D3; specs: ci-apply, release-credentials, repositories)

- [x] 1.1 Write `scripts/tests/test_main_only_environments.py`, marked `tofu` (`pytestmark`), with the D1 table and
      the mutation tests listed in D3 first, against a problems function that returns nothing yet. Verify each
      mutation test fails, and record the count
      Done 2026-10-18: `18 failed, 1 passed`. Every failure is the stub's `[]` against the named problem, or `DID NOT
      RAISE ValueError` for the two unknown shapes; none came from the text edits. The pass is the real files
- [x] 1.2 Write the reader (D2): strip comments, find resource blocks by matching braces, read `local.ci_environments`,
      resolve the `ci` resource's `dynamic` conditions and the policy's `for_each` filter, and refuse any other shape
      with "update this test". Write the problems function (D1, D3) on top of it. Verify every test in the module
      passes, including the real files giving no problems
      Done 2026-10-18: `19 passed`. The reader finds all five environments (`plan-pr` too, which isn't checked), each
      with `can_admins_bypass` false, the four main-only ones with `protected_branches = false` and
      `custom_branch_policies = true`, `apply` and `plan-pr` with `local.owner_user_id` as reviewer, and exactly
      `['main']` as the branch policies of each main-only one. ruff and mypy are clean
- [x] 1.3 Delete the `github_pages` resource block in a scratch copy of `tofu/environments.tf` (in the scratchpad,
      read by the problems function, not the real file) and run the real-files check against it. Verify it names
      `github-pages: not declared`. This is #61's failing case, the one `prevent_destroy` missed
      Done 2026-10-18, on copies of both files in the scratchpad. With only the environment's block deleted, its policy
      still names it, and the check refuses with `github_repository_environment.github_pages isn't declared` (as
      `tofu validate` would). With the block and its policy deleted, which is the `2 to destroy` from #61, it gives
      `['github-pages: not declared']`
- [x] 1.4 Verify `uv run scripts/check.py` passes, and that `uv run scripts/check.py --scope tofu` runs the new tests
      (`guard_pytest` accepts their marker)
      Done 2026-10-18: `check: all gates passed` both ways. `--scope tofu` selected 58 of 971 tests, including all 19 in
      `test_main_only_environments.py`

## 2. The comments (D4)

- [x] 2.1 Correct the `lifecycle` comment on `github_repository_environment.github_pages` in `tofu/environments.tf`
      (D4), and add a one-line comment naming the test to the `ci` and `release` declarations. Verify
      `tofu fmt -check -recursive tofu` and `tofu validate` pass, and the module's tests still pass
      Done 2026-10-18: the `ci` declarations share `environments.tf`'s header, so the line naming the test went there,
      covering `github_pages` too. `tofu fmt -check` is clean, `tofu validate` reports `Success!`, and the module's
      tests: `19 passed`
- [x] 2.2 Commit group 1, then group 2, as Conventional Commits, signed off, saying why. Verify the guard accepts
      each commit
      Done 2026-10-18: group 1 `1afc3d3` (the guard ran the full check: `971 passed`, all gates passed), group 2
      `f33b71d` (`check.py --scope tofu`: `58 passed`, all gates passed). Both signed off

## 3. Pull request

- [ ] 3.1 Fast-forward onto `origin/main`, then open the pull request with `Closes #61`, 1.1's failing count, 1.3's
      output and 1.4's check result. Verify CI is green on every job and that the posted plan reads `No changes.` (or
      only drift already on `main`, named in the PR) once the owner approves that run

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- Comment on #61 with the PR and the archived change. Check #61 is closed and its card says Done.
- The README.md follow-up is #85 (opened 2026-10-18, on the roadmap); it isn't part of this change.
- Remove this change's branch and worktree once it's merged and verified.
