# Tasks

## 1. The check (D1 to D3; specs: ci-apply, release-credentials, repositories)

- [ ] 1.1 Write `scripts/tests/test_main_only_environments.py`, marked `tofu` (`pytestmark`), with the D1 table and
      the mutation tests listed in D3 first, against a problems function that returns nothing yet. Verify each
      mutation test fails, and record the count
- [ ] 1.2 Write the reader (D2): strip comments, find resource blocks by matching braces, read `local.ci_environments`,
      resolve the `ci` resource's `dynamic` conditions and the policy's `for_each` filter, and refuse any other shape
      with "update this test". Write the problems function (D1, D3) on top of it. Verify every test in the module
      passes, including the real files giving no problems
- [ ] 1.3 Delete the `github_pages` resource block in a scratch copy of `tofu/environments.tf` (in the scratchpad,
      read by the problems function, not the real file) and run the real-files check against it. Verify it names
      `github-pages: not declared`. This is #61's failing case, the one `prevent_destroy` missed
- [ ] 1.4 Verify `uv run scripts/check.py` passes, and that `uv run scripts/check.py --scope tofu` runs the new tests
      (`guard_pytest` accepts their marker)

## 2. The comments (D4)

- [ ] 2.1 Correct the `lifecycle` comment on `github_repository_environment.github_pages` in `tofu/environments.tf`
      (D4), and add a one-line comment naming the test to the `ci` and `release` declarations. Verify
      `tofu fmt -check -recursive tofu` and `tofu validate` pass, and the module's tests still pass
- [ ] 2.2 Commit group 1, then group 2, as Conventional Commits, signed off, saying why. Verify the guard accepts
      each commit

## 3. Pull request

- [ ] 3.1 Fast-forward onto `origin/main`, then open the pull request with `Closes #61`, 1.1's failing count, 1.3's
      output and 1.4's check result. Verify CI is green on every job and that the posted plan reads `No changes.` (or
      only drift already on `main`, named in the PR) once the owner approves that run

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- Comment on #61 with the PR and the archived change. Check #61 is closed and its card says Done.
- The README.md follow-up is #85 (opened 2026-10-18, on the roadmap); it isn't part of this change.
- Remove this change's branch and worktree once it's merged and verified.
