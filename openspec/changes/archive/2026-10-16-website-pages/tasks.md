# Tasks

## 1. The App can read and update the website's Pages site

- [x] 1.1 Read GitHub's REST reference for "Get a GitHub Pages site" and "Update information about a GitHub Pages
      site", and record the fine-grained permissions each needs in this task (design D5). Verify by quoting the two
      permission lines and their URLs
      Done 2026-10-16. https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps lists,
      under Repository permissions for "Pages": `GET /repos/{owner}/{repo}/pages | read | UAT, IAT | ✗` and
      `PUT /repos/{owner}/{repo}/pages | write | UAT, IAT | ✓`; under "Administration" it lists only the PUT. The
      endpoint pages (https://docs.github.com/en/rest/pages/pages) give no fine-grained line. So reading the site needs
      Pages read, which the App doesn't have: 1.3 is expected to be refused. (1.3 shows it wasn't: the table
      doesn't match what GitHub does for this App on a public repository)
- [x] 1.2 Add the `pages` variable to `tofu/modules/repository/variables.tf` and the counted `github_repository_pages`
      resource to `tofu/modules/repository/main.tf`, with `build_type = "workflow"`, no `source`, and
      `prevent_destroy`, each commented with why (design D2, D3). Set `pages = { cname = "troupe.run" }` on
      `repo_website` in `tofu/repositories.tf`, and replace the stale comment above it with one saying what's declared
      and that a domain removed by hand takes two applies to restore (design, Risks). Add the `import` block to
      `tofu/imports.tf` (design D4). Verify `tofu fmt -check` and `tofu validate` are clean
      Done 2026-10-16: `tofu fmt -check -recursive` clean; `uv run scripts/check.py`: all gates passed, `tofu validate`
      included
- [x] 1.3 Fast-forward onto `origin/main` and run a local plan. If the App's read of the site is refused, stop and ask
      the owner to add Pages read and write to `troupe-run-infrastructure` and accept it on the org's installation
      (design D5), then plan again. Verify, and record here, which it was: the plan read the site with the existing
      permissions, or after the owner's change (with the date)
      Done 2026-10-16, on 92e2554 (0 commits behind `origin/main`): the plan read the site with the existing
      permissions. The App's installation still has no Pages permission (`gh api orgs/troupe-run/installations`:
      actions_variables, administration, contents, issues, members, organization_administration and workflows
      write; metadata read). Whether a corrective apply can write without it isn't known: the PUT is also listed under
      Administration write, which the App has. If one is ever refused, D5's step applies then
- [x] 1.4 Only if 1.3 needed the permission: add `"pages": "write"` to `troupe-run-infrastructure` in
      `oob/app-installations.json`. Verify `uv run scripts/oob.py` reports no drift, and quote its output
      Reopened 2026-10-16: 1.3 read the site without the permission, but 3.2 showed the App can't update one (403).
      The owner chose to add Pages read and write, and `oob/app-installations.json` now records `"pages": "write"`.
      Done 2026-10-16, after the owner's change: the installation reports `pages: write`, and `uv run scripts/oob.py`
      reports no difference in App installations. Its four other differences are troupe's `cap:*` labels
      (`flake-hunt`, `python-support` and `quality-check` have no label, and `cap:releases` has no recorded Purpose),
      which are on `main` too and outside this change

## 2. Adopting the site changes nothing, and nothing can disable it

- [x] 2.1 Read the local plan from 1.3. Verify it says `1 to import, 0 to add, 0 to change, 0 to destroy`, that the
      import is `module.repo_website.github_repository_pages.this[0]`, and that it shows `cname = "troupe.run"`,
      `https_enforced = true` and `build_type = "workflow"`. Record the summary line. If anything is planned to
      change, fix the configuration, never the site
      Done 2026-10-16: `Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.` The one import is
      `module.repo_website.github_repository_pages.this[0]` (imported from "website", id 1408722166), with
      `build_type = "workflow"`, `cname = "troupe.run"`, `https_enforced = true` and `public = true`, and no `source`
- [x] 2.2 Temporarily remove `pages` from `repo_website` and run a local plan. Verify it fails on `prevent_destroy` for
      the Pages resource, and record the error. Revert the edit, and verify `git diff` shows it gone
      Done 2026-10-16, with one step added: as written, the plan stops first on "Configuration for import target does
      not exist", because before the apply the site isn't in state, so there's nothing to refuse. So the site was
      imported into the local state file only (`tofu.py import`, which reads GitHub and writes nothing there), and
      the plan ran with `pages` and the import block both commented out: `Plan: 0 to add, 0 to change, 1 to
      destroy.`, then `Error: Resource instance cannot be destroyed ... module.repo_website.github_repository_pages.
      this[0] has prevent_destroy set`. `git checkout` restored `repositories.tf`, `imports.tf` and
      `terraform.tfstate`; `git status` shows no tofu changes, and `cmp` with a copy taken first says the state is
      identical
- [x] 2.3 In the README's "Changing the org", add the Pages resource's address to the `removed`-block guidance, so
      stopping management forgets the site rather than disabling it (design D3). Verify the address matches the one in
      2.1's plan
      Done 2026-10-16: README "Changing the org" gains "An apply can't disable the website", with a `removed` block
      for `module.repo_website.github_repository_pages.this[0]`, the address 2.1 imports and 2.2 refuses to destroy
      Corrected 2026-10-16, after archiving: that block didn't work. Tested the same way as 2.2 (imported into the
      local state only, then restored, with `cmp` identical): `from = ...this[0]` fails with "Resource instance address
      with keys is not allowed", and `from = ...this` fails with "Removed resource block still exists" while the
      counted block is in the module. With the block deleted from the module, `pages` removed and
      `from = module.repo_website.github_repository_pages.this`: `Plan: 0 to add, 0 to change, 0 to destroy, 1 to
      forget.` The README now gives that procedure. It also no longer claims that removing the module is refused:
      `prevent_destroy` goes with its block (found by website-environment, #52), so there the owner's review of the plan
      is the gate. The spec and design say the same

## 3. Drift in the Pages settings shows in a plan (probe)

- [x] 3.1 Add a `probe_pages` option to `tofu/probe/main.tf` that declares a `github_repository_pages` with
      `build_type = "workflow"` on the probe repository, and describe it in the file's header with the other probes
      (design D6). Verify `tofu validate` is clean in `tofu/probe`
      Done 2026-10-16: `probe_pages` declares `github_repository_pages.probe` (workflow, no domain) and imports it.
      `tofu fmt -check` clean and `tofu validate` passed in `tofu/probe`
- [x] 3.2 Run the probe: create a throwaway public repository, ask the owner to add it to the App's installation,
      turn on Pages deployed from Actions with `gh api`, import and plan with `probe_pages = true` and verify no change.
      Then switch its source to a branch with `gh api`, plan again, and verify the plan shows `build_type` changing
      back to `workflow`. Record both plans' summary lines here
      2026-10-16, on `troupe-run/infra-probe-pages-20261016` (added to the App's installation by the owner), with
      `declared = false` so only the Pages site is touched: the import plans `1 to import, 0 to add, 0 to change, 0
      to destroy`, and was applied into the probe's state. After `gh api -X PUT ... -f build_type=legacy -f
      "source[branch]=main"`, the plan shows `~ build_type = "legacy" -> "workflow"` and the `source` block removed:
      `Plan: 0 to add, 1 to change, 0 to destroy.` Applying that correction failed: `PUT .../pages: 403 Resource not
      accessible by integration`. The App can read a Pages site but not update one, so drift shows but can't be
      corrected without the Pages permission (design D5). After the owner added Pages read and write, the same
      correction applied (`Apply complete! Resources: 0 added, 1 changed, 0 destroyed.`), the API reads
      `build_type: workflow` again, and the next plan says `No changes.`
- [x] 3.3 Delete the throwaway repository, the probe's state, and its `terraform.tfvars`, and ask the owner to confirm
      it's gone from the App's installation. Verify `gh repo view troupe-run/<name>` fails and `git status` in
      `tofu/probe` is clean
      Done 2026-10-16: `gh repo delete` succeeded and `gh repo view` now fails ("Could not resolve to a Repository");
      `terraform.tfstate`, its backup and `terraform.tfvars` are deleted, and `git status` in `tofu/probe` shows only
      the ignored `.terraform/` and lock file. GitHub drops a deleted repository from an App's installation; the owner
      was asked to confirm it's gone from the list
- [x] 3.4 Record here how the custom-domain and HTTPS scenarios are shown (design D6): cite the lines of
      `resource_github_repository_pages.go` at `v6.13.0` where Read sets `cname` and `https_enforced` from the API,
      and say that this is reasoning from the provider's source, not a run against a live domain
      Done 2026-10-16. In `github/resource_github_repository_pages.go` at `v6.13.0`,
      `resourceGithubRepositoryPagesRead` (line 239) sets `cname` from `pages.GetCNAME()` on every refresh (lines
      258 to 266: the API's value, or null when it has none) and `https_enforced` from `pages.GetHTTPSEnforced()`
      (line 285). Both are compared with the declaration, so a domain or HTTPS changed by hand is a planned change.
      This is reasoning from the provider's source, not a run: `troupe.run` can't be lent to a probe. 3.2 shows the
      same refresh-and-compare path working for `build_type`

## 4. Evidence on GitHub

- [x] 4.1 Run `uv run scripts/check.py`, then push the branch and open the pull request (`Closes #51`). Verify its
      checks pass and, once the owner approves the run, that its posted plan matches 2.1. Record it here
      2026-10-16, PR #57 at 992e566: every guard tests leg, `check` and DCO passed. After the owner approved it,
      `plan (pull request)` passed, and its comment says `Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.`,
      importing only `module.repo_website.github_repository_pages.this[0]`, as in 2.1

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging. The owner merges by rebase and approves `main`'s `apply` job.
- After the apply, verify `gh api repos/troupe-run/website/pages` reports the same `cname`, `https_enforced` and
  `build_type` as before, and that https://troupe.run answers 200.
- Comment on #51 with the pull request and the archived change, check it's closed, and set its card to Done.
- If #52's change is still open, rebase it onto `main` after this one's state commit, and plan again.
