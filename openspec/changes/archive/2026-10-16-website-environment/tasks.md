# Tasks

## 1. Adopt the environment as it is (D1, D2 step 1, D4, D5)

- [x] 1.1 Before writing anything, re-read the live environment and its policies
      (`gh api repos/troupe-run/website/environments/github-pages` and `.../deployment-branch-policies`). Verify they
      still match design.md's Context: `can_admins_bypass: true`, custom branch policies only, no reviewers or wait
      timer, and one policy, `main`, ID `62248502`. If anything differs, stop and update the design first
      Done 2026-10-16: `can_admins_bypass: true`, custom branch policies only, one `branch_policy` rule, one policy
      `main` (ID `62248502`). Matches the design
- [x] 1.2 In `tofu/environments.tf`, add `github_repository_environment.github_pages` on `module.repo_website.name`
      with the live values (`can_admins_bypass = true` for now, `prevent_self_review = false`, the
      `deployment_branch_policy` block, `lifecycle { prevent_destroy = true }` with a comment naming the `removed`
      block as the way out), and `github_repository_environment_deployment_policy.github_pages_main_only`
      (`branch_pattern = "main"`). Widen the file's header and table to cover the website's deploy environment, citing
      spec: repositories and #52. Add the two `import` blocks to `tofu/imports.tf` (`website:github-pages`,
      `website:github-pages:62248502`). Verify `uv run scripts/check.py` passes (`tofu fmt -check`, `tofu validate`)
      Done 2026-10-16: all gates passed (802 tests, `tofu fmt`, `tofu validate`)
- [x] 1.3 Add a `tofu/environments.tf` row to README.md's Layout table, saying it holds CI's three environments on
      infrastructure and the website's `github-pages`, limited to `main`. Verify `uv run scripts/check.py` passes
      Done 2026-10-16: all gates passed
- [x] 1.4 Fast-forward onto `origin/main`, then run a local plan. Verify its summary is
      `Plan: 2 to import, 0 to add, 0 to change, 0 to destroy.`, with the environment and the policy as the two imports.
      Record the summary here. If it shows any change, fix the declaration to match GitHub and re-plan before going on
      Done 2026-10-16, on 4268fb7's state: `Plan: 2 to import, 0 to add, 0 to change, 0 to destroy.` The two imports
      are the environment and `github_pages_main_only`, with no attribute changes
- 1.5 (moved to the workflow follow-up, owner 2026-10-16) `prevent_destroy` can only be checked once the environment
      is in state, which the apply's import does. Before that, removing the declaration only drops the pending import,
      so no plan fails
- [x] 1.6 Commit the adoption (`feat(tofu): adopt the website's github-pages environment and its main-only policy`)
      Done 2026-10-16: 770d906

## 2. No admin can bypass it (D2 step 2, D3)

- [x] 2.1 Set `can_admins_bypass = false`, with a comment giving D3's reason (an admin, which agents share the
      login of, could otherwise deploy past the branch rule), and commit it. Verify `uv run scripts/check.py` passes,
      and a local plan's summary is `Plan: 2 to import, 0 to add, 1 to change, 0 to destroy.`, where the one change is
      `can_admins_bypass` from `true` to `false` on the environment and nothing else. Record the summary here
      Done 2026-10-16, on 4268fb7's state: all gates passed. `Plan: 2 to import, 0 to add, 1 to change, 0 to destroy.`
      The one change is `can_admins_bypass = true -> false` on `github_repository_environment.github_pages`, imported
      and updated in place. The same update also shows `+ prevent_self_review = false`: GitHub returns that field
      only for an environment with reviewers, so the import leaves it empty in state, and the update writes GitHub's
      own default. Nothing changes on GitHub for it, and `plan-main` (no reviewers, `false`) shows no drift daily

## 3. Evidence on GitHub

- [x] 3.1 Push the branch and open the pull request (`Closes #52`). Verify every check passes, and that after the
      owner approves the plan run, its posted plan matches 2.1's
      Done 2026-10-16, PR #56 at 9ef6168: `check`, DCO, `does it need a plan?`, both `guard (workflow rules)` runs
      and all eleven `guard tests` legs passed. After the owner approved it, `plan (pull request)` passed, and its
      comment matches 2.1 line for line: `Plan: 2 to import, 0 to add, 1 to change, 0 to destroy.`

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging, syncing the `repositories` delta. The owner merges by rebase and
  approves `main`'s `apply` job.
- After the apply, verify with `gh api repos/troupe-run/website/environments/github-pages` that `can_admins_bypass` is
  `false`, the protection rule is still `branch_policy`, and `.../deployment-branch-policies` still lists only
  `main`. Then verify the next deploy of the website's `main` succeeds and https://troupe.run answers 200 (spec
  scenario "main still deploys"). If no website change is pending, re-run the latest Deploy run.
- After the apply, check `prevent_destroy` (task 1.5): with `github_repository_environment.github_pages`, its import
  and the policy commented out locally (not committed), a local plan fails with OpenTofu's `prevent_destroy` error
  naming the environment. Restore the file, check `git diff` is empty, and record the error line on #52.
- After #51's apply (whichever lands second), re-read the environment and check `main`'s next plan shows no drift on
  it (design, Risks).
- Comment on #52 with the pull request and the archived change, check it's closed, and set its card to Done.
