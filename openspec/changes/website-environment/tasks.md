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
- [ ] 1.5 Verify `prevent_destroy` works: with the environment's resource commented out locally (not committed), a
      plan fails with OpenTofu's `prevent_destroy` error naming `github_repository_environment.github_pages`. Restore
      the file, check `git diff` shows nothing from this task, and record the error line here
- [x] 1.6 Commit the adoption (`feat(tofu): adopt the website's github-pages environment and its main-only policy`)
      Done 2026-10-16: 770d906

## 2. No admin can bypass it (D2 step 2, D3)

- [x] 2.1 Set `can_admins_bypass = false`, with a comment giving D3's reason (an admin, which agents share the
      login of, could otherwise deploy past the branch rule), and commit it. Verify `uv run scripts/check.py` passes,
      and a local plan's summary is `Plan: 2 to import, 0 to add, 1 to change, 0 to destroy.`, where the one change is
      `can_admins_bypass` from `true` to `false` on the environment and nothing else. Record the summary here
      Done 2026-10-16, on 4268fb7's state: all gates passed. `Plan: 2 to import, 0 to add, 1 to change, 0 to destroy.`
      The one change is `can_admins_bypass = true -> false` on `github_repository_environment.github_pages`, imported
      and updated in place

## 3. Evidence on GitHub

- [ ] 3.1 Push the branch and open the pull request (`Closes #52`). Verify every check passes, and that after the
      owner approves the plan run, its posted plan matches 2.1's

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging, syncing the `repositories` delta. The owner merges by rebase and
  approves `main`'s `apply` job.
- After the apply, verify with `gh api repos/troupe-run/website/environments/github-pages` that `can_admins_bypass` is
  `false`, the protection rule is still `branch_policy`, and `.../deployment-branch-policies` still lists only
  `main`. Then verify the next deploy of the website's `main` succeeds and https://troupe.run answers 200 (spec
  scenario "main still deploys"). If no website change is pending, re-run the latest Deploy run.
- After #51's apply (whichever lands second), re-read the environment and check `main`'s next plan shows no drift on
  it (design, Risks).
- Comment on #52 with the pull request and the archived change, check it's closed, and set its card to Done.
