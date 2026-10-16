# Tasks

## 1. The App can read and update the website's Pages site

- [x] 1.1 Read GitHub's REST reference for "Get a GitHub Pages site" and "Update information about a GitHub Pages
      site", and record the fine-grained permissions each needs in this task (design D5). Verify by quoting the two
      permission lines and their URLs
      Done 2026-10-16. https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps lists,
      under Repository permissions for "Pages": `GET /repos/{owner}/{repo}/pages | read | UAT, IAT | ✗` and
      `PUT /repos/{owner}/{repo}/pages | write | UAT, IAT | ✓`; under "Administration" it lists only the PUT. The
      endpoint pages (https://docs.github.com/en/rest/pages/pages) give no fine-grained line. So reading the site needs
      Pages read, which the App doesn't have: 1.3 is expected to be refused
- [x] 1.2 Add the `pages` variable to `tofu/modules/repository/variables.tf` and the counted `github_repository_pages`
      resource to `tofu/modules/repository/main.tf`, with `build_type = "workflow"`, no `source`, and
      `prevent_destroy`, each commented with why (design D2, D3). Set `pages = { cname = "troupe.run" }` on
      `repo_website` in `tofu/repositories.tf`, and replace the stale comment above it with one saying what's declared
      and that a domain removed by hand takes two applies to restore (design, Risks). Add the `import` block to
      `tofu/imports.tf` (design D4). Verify `tofu fmt -check` and `tofu validate` are clean
      Done 2026-10-16: `tofu fmt -check -recursive` clean; `uv run scripts/check.py`: all gates passed, `tofu validate`
      included
- [ ] 1.3 Fast-forward onto `origin/main` and run a local plan. If the App's read of the site is refused, stop and ask
      the owner to add Pages read and write to `troupe-run-infrastructure` and accept it on the org's installation
      (design D5), then plan again. Verify, and record here, which it was: the plan read the site with the existing
      permissions, or after the owner's change (with the date)
- [ ] 1.4 Only if 1.3 needed the permission: add `"pages": "write"` to `troupe-run-infrastructure` in
      `oob/app-installations.json`. Verify `uv run scripts/oob.py` reports no drift, and quote its output

## 2. Adopting the site changes nothing, and nothing can disable it

- [ ] 2.1 Read the local plan from 1.3. Verify it says `1 to import, 0 to add, 0 to change, 0 to destroy`, that the
      import is `module.repo_website.github_repository_pages.this[0]`, and that it shows `cname = "troupe.run"`,
      `https_enforced = true` and `build_type = "workflow"`. Record the summary line. If anything is planned to
      change, fix the configuration, never the site
- [ ] 2.2 Temporarily remove `pages` from `repo_website` and run a local plan. Verify it fails on `prevent_destroy` for
      the Pages resource, and record the error. Revert the edit, and verify `git diff` shows it gone
- [ ] 2.3 In the README's "Changing the org", add the Pages resource's address to the `removed`-block guidance, so
      stopping management forgets the site rather than disabling it (design D3). Verify the address matches the one in
      2.1's plan

## 3. Drift in the Pages settings shows in a plan (probe)

- [ ] 3.1 Add a `probe_pages` option to `tofu/probe/main.tf` that declares a `github_repository_pages` with
      `build_type = "workflow"` on the probe repository, and describe it in the file's header with the other probes
      (design D6). Verify `tofu validate` is clean in `tofu/probe`
- [ ] 3.2 Run the probe: create a throwaway public repository, ask the owner to add it to the App's installation,
      turn on Pages deployed from Actions with `gh api`, import and plan with `probe_pages = true` and verify no change.
      Then switch its source to a branch with `gh api`, plan again, and verify the plan shows `build_type` changing
      back to `workflow`. Record both plans' summary lines here
- [ ] 3.3 Delete the throwaway repository, the probe's state, and its `terraform.tfvars`, and ask the owner to confirm
      it's gone from the App's installation. Verify `gh repo view troupe-run/<name>` fails and `git status` in
      `tofu/probe` is clean
- [ ] 3.4 Record here how the custom-domain and HTTPS scenarios are shown (design D6): cite the lines of
      `resource_github_repository_pages.go` at `v6.13.0` where Read sets `cname` and `https_enforced` from the API,
      and say that this is reasoning from the provider's source, not a run against a live domain

## 4. Evidence on GitHub

- [ ] 4.1 Run `uv run scripts/check.py`, then push the branch and open the pull request (`Closes #51`). Verify its
      checks pass and, once the owner approves the run, that its posted plan matches 2.1. Record it here

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging. The owner merges by rebase and approves `main`'s `apply` job.
- After the apply, verify `gh api repos/troupe-run/website/pages` reports the same `cname`, `https_enforced` and
  `build_type` as before, and that https://troupe.run answers 200.
- Comment on #51 with the pull request and the archived change, check it's closed, and set its card to Done.
- If #52's change is still open, rebase it onto `main` after this one's state commit, and plan again.
