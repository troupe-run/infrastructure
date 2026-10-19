# Tasks

Group 1 needs nothing from the owner, so it can start before D1 is decided. Groups 3 to 5 need the App from group 2.
If the owner chooses option B in D1, stop after 2.1 and update the change (`/opsx:update`) before going on.

## 1. The `docs` environment

- [x] 1.1 Add `("repo_troupe", "docs"): False` to `MAIN_ONLY` in `scripts/tests/test_main_only_environments.py`, and
      `tofu/docs.tf` to `TF_FILES` (design D6). Verify that
      `uv run pytest scripts/tests/test_main_only_environments.py` fails, naming `docs` as not declared, before 1.2
- [x] 1.2 Add `tofu/docs.tf` (design D3, D6): the `docs` environment on `module.repo_troupe`, with
      `can_admins_bypass = false`, `prevent_self_review = false`, no reviewers and custom branch policies, plus its
      `main`-only deployment policy, each with a comment naming the spec (docs-build-credentials). Verify that the
      test from 1.1 passes and that `uv run scripts/check.py` passes (tofu fmt, validate)
- [x] 1.3 Check the test catches weakening, not only removal. On a scratch copy, set `can_admins_bypass = true`, and
      separately change the policy's `branch_pattern` to `*`. Verify the test fails each time, naming `docs` and what
      changed, then restore the file
- [x] 1.4 Add `tofu/docs.tf` to README.md's layout table. Verify `uv run scripts/check.py` passes

## 2. The App (owner, on GitHub and in 1Password)

- [x] 2.1 Owner: decide design D1 (a new `troupe-run-docs` App, the release App, or the infrastructure App) and
      record it in design.md as "(owner, <date>)". Verify that design.md's D1 no longer says OPEN QUESTION. Done: option
      A, a new App (owner, 2026-10-19), and D1 says so
- [x] 2.2 Owner: create the GitHub App `troupe-run-docs` in the troupe-run org, installable only on this account, with
      the webhook off. Repository permission: Actions read and write, and nothing else beyond the metadata GitHub always
      grants. No organisation permission. Install it on `troupe-run/website` only. Verify with
      `gh api orgs/troupe-run/installations --jq '.installations[] | select(.app_slug=="troupe-run-docs") | {permissions, repository_selection}'`,
      which should show `actions: write`, `metadata: read` and `selected`. Found (2026-10-19): App ID 5380996,
      installation 173027176, `actions: write`, `metadata: read`, `selected`, and no webhook events. The repository list
      is checked with the App's own token in 3.5
- [x] 2.3 Owner: generate a private key, store it in 1Password as `troupe-run-docs`, field `private key`, in vault
      `troupe.run`, and delete the downloaded file. Verify that
      `op read -n "op://troupe.run/troupe-run-docs/private key" | head -c 31` prints only the PEM header. Found: with
      `OP_ACCOUNT=l-a-u.1password.com`, it prints `-----BEGIN RSA PRIVATE KEY-----`
- [x] 2.4 Record the App's ID and client ID on #109. Verify the comment exists. Done: #109 issuecomment-6267530696

## 3. Probe the token (design D5)

- [x] 3.1 Create `troupe-run/infra-probe-docs-trigger` with a workflow that has `on: workflow_dispatch` and one job that
      echoes its ref, and add it to the docs App's installation (owner accepts on GitHub). Verify the repository and
      workflow exist with `gh workflow list -R troupe-run/infra-probe-docs-trigger`, and the installation lists it.
      Done: workflow `probe` (389402012), and the owner added the repository to installation 173027176
- [x] 3.2 Mint an installation token locally from the 1Password key for the probe repository, without printing it. Use
      it to create a `workflow_dispatch` event on `main`. Record in design.md D5 whether a run starts. Verify with
      `gh run list -R troupe-run/infra-probe-docs-trigger --event workflow_dispatch`. Done: 204, and run 39254721925
      started on `main` and succeeded (design D5, Findings)
- [x] 3.3 With the same token, try to create a branch (`POST git/refs`), a tag, and a file (`PUT contents/<path>`) in
      the probe repository. Verify each is refused with 403, that
      `gh api repos/troupe-run/infra-probe-docs-trigger/git/refs` shows nothing new, and record that in D5. Done: 403
      for each, and the refs are `refs/heads/main` only (design D5, Findings)
- [x] 3.4 If 3.2 needed another permission, the owner adds it to the App and accepts it on the installation, and the
      spec's permission line changes to match. Verify that 3.2 then succeeds and that
      `openspec validate docs-build-trigger --strict` passes. Mark not needed if 3.2 succeeded as it is. Not needed: 3.2
      succeeded with `actions: write` alone
- [x] 3.5 Remove the probe repository from the App's installation and delete it. Verify the repository returns 404,
      and the installation's repositories are website only. Done: deleting the repository removed it from the
      installation; it returns 404, and the App's own token lists `troupe-run/website` only

## 4. The declarations that name the App

- [x] 4.1 Add `troupe-run-docs` to `oob/app-installations.json` with the permissions found in group 3 and
      `repository_selection: selected` (design D6). Verify `uv run scripts/oob.py` reports no difference for App
      installations, where before this edit it reported the new App. Done: before, "'troupe-run-docs' is on GitHub
      but not declared"; after, no differences
- [x] 4.2 Add `DOCS_APP_CLIENT_ID` to `tofu/docs.tf`, holding the client ID from 2.4 in a `locals` block, as a
      `github_actions_variable` on `module.repo_troupe`. Verify `uv run scripts/check.py` passes
- [x] 4.3 Document the steps done by hand in `oob/README.md` (design D6): a "The docs App (set up by hand)" section
      with creating and installing the App, storing and setting the key, checking it by name, and rotating it. Add a
      row for `troupe-run-docs` with `website` to the table of repositories, confirmed with the date. Verify the
      documented `gh api` check commands run as written

## 5. The plan

- [ ] 5.1 Open the pull request (`Closes #109`), saying that the website's side and troupe's sending step are
      website#23's (design D4), and get CI's plan. Verify the plan creates only the `docs` environment, its deployment
      policy and `DOCS_APP_CLIENT_ID` on troupe, changes no ruleset, and touches no secret

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`).
- After the merge and CI's apply (these can't be ticked before archive, so they're not tracked tasks):
  - Owner: set the secret with
    `op read -n "op://troupe.run/troupe-run-docs/private key" | gh secret set DOCS_APP_PRIVATE_KEY --env docs -R troupe-run/troupe`,
    and check it by name: `gh api repos/troupe-run/troupe/environments/docs/secrets --jq '.secrets[].name'` prints
    `DOCS_APP_PRIVATE_KEY`.
  - Comment on troupe-run/website#23 that the credential is ready, with design D4's constraints.
- After the merge, comment on #109 with the PR and the archived change, close it if the PR didn't, and check the card
  says Done.
