# Tasks

## 1. The App (owner, on GitHub and in 1Password)

- [x] 1.1 Owner: create the GitHub App `troupe-run-release` in the troupe-run org, installable only on this account,
      with the webhook off. Repository permissions: contents, pull requests and issues read/write, metadata read.
      No organisation or account permissions (spec: release-credentials). Install it on `troupe-run/troupe` only.
      Verify with `gh api orgs/troupe-run/installations --jq '.installations[] | select(.app_slug=="troupe-run-release")
      | {permissions, repository_selection}'`, which shows exactly those permissions and `selected`. Then confirm in
      the App's installation settings that the only repository is `troupe`
- [x] 1.2 Owner: generate a private key, store it in 1Password as `troupe-run-release`, field `private key`, in vault
      `troupe.run` (design D4), and delete the downloaded file. Verify `op read -n
      "op://troupe.run/troupe-run-release/private key" | head -c 31` prints `-----BEGIN RSA PRIVATE KEY-----`
      (the header only)
- [x] 1.3 Record on #34 the App's ID and client ID, and its bot user ID from `gh api
      'users/troupe-run-release%5Bbot%5D' --jq .id`. Verify the comment exists. #33 and troupe's `signoff` read the
      bot ID from it
- [x] 1.4 Owner (design D3, option A): add the repository permission "Variables: write" to `troupe-run-infrastructure`
      and accept it on the org's installation. Verify `gh api orgs/troupe-run/installations` shows
      `actions_variables: write` for it

## 2. The declarations

- [x] 2.1 Add `troupe-run-release` to `oob/app-installations.json` (design D1). Add `actions_variables: write`
      to `troupe-run-infrastructure`. Verify `uv run scripts/oob.py` reports no
      difference for App installations, where before this edit it reported the new App
- [x] 2.2 Add `tofu/labels/release.json` with `autorelease: pending` and `autorelease: tagged` (design D5), and
      concatenate it into `repo_troupe`'s labels. Add a test to `scripts/tests/test_labels.py` that the release set
      holds exactly those two names, each with a description of 100 characters or fewer. Name the test for that, and
      verify it fails when a name is misspelt. Then verify `uv run scripts/check.py` passes
- [ ] 2.3 Add `tofu/release.tf` (design D2, D3): the `release` environment on troupe, its `main` deployment policy,
      and `RELEASE_APP_CLIENT_ID` with the client ID from 1.3, each with a comment naming the spec. Verify `uv run scripts/check.py` passes (tofu fmt, validate)
- [ ] 2.4 Document the steps done by hand in `oob/README.md` (design D4): creating and installing the App, storing
      and setting the key, rotating it, and a row for `troupe-run-release` with `troupe` in the table of
      repositories, confirmed by the owner with today's date. Add `tofu/release.tf` and `tofu/labels/release.json`
      to README.md's layout table. Verify the documented `gh api` check commands run as written, and that
      `uv run scripts/check.py` passes

## 3. Evidence

- [ ] 3.1 Run `uv run scripts/tofu.py plan`. Verify it creates exactly the `release` environment, its deployment
      policy, the variable and troupe's two labels. Verify it changes and destroys nothing, and leaves
      troupe's ruleset's bypass actors unchanged (spec: release-credentials). Grep every `+`, `~` and `-` line, and
      keep the plan for the pull request
- [ ] 3.2 Run `uv run scripts/oob.py` and verify it reports no difference. Keep its output for the pull request
- [ ] 3.3 Run `openspec validate release-app --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #34`, the plan from 3.1 and `oob.py`'s output from 3.2. Tell the owner the run
  link while the `plan (pull request)` run waits for approval.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job.
- After the apply, the owner sets the key (design D4). Verify `gh api repos/troupe-run/troupe/environments/release`
  shows `can_admins_bypass: false` and custom branch policies, with `.../deployment-branch-policies` listing only
  `main`. Verify `.../environments/release/secrets` lists `RELEASE_APP_PRIVATE_KEY` by name, `gh variable list -R
  troupe-run/troupe` shows `RELEASE_APP_CLIENT_ID`, and `gh label list -R troupe-run/troupe --search autorelease`
  shows both labels.
- Comment on #34 with the pull request and the archived change, then tell troupe-run/troupe#23 and #33 that the App and
  its bot ID are ready.
