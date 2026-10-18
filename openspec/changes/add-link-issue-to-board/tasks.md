# Tasks

Group 1 needs nothing from the owner, so it can start before the App exists. Groups 3 and 4 need the App from
group 2.

## 1. The `board` environment

- [x] 1.1 Add `"board": Expected("repo_website", owner_reviews=False)` to `MAIN_ONLY` in
      `scripts/tests/test_main_only_environments.py`, and `tofu/board.tf` to `TF_FILES` (design D3). Verify that
      `uv run pytest scripts/tests/test_main_only_environments.py` fails, naming `board` as not declared, before 1.2
- [x] 1.2 Add `tofu/board.tf` (design D2): the `board` environment on `module.repo_website`, with
      `can_admins_bypass = false`, `prevent_self_review = false`, no reviewers and custom branch policies, plus its
      `main`-only deployment policy, each with a comment naming the spec (board-credentials). Verify that the test from
      1.1 passes and that `uv run scripts/check.py` passes (tofu fmt, validate)
- [x] 1.3 Check the test catches weakening, not only removal. On a scratch copy, set `can_admins_bypass = true`, and
      separately change the policy's `branch_pattern` to `*`. Verify the test fails each time, naming `board` and
      what changed, then restore the file
- [x] 1.4 Add `tofu/board.tf` to README.md's layout table. Verify `uv run scripts/check.py` passes

## 2. The App (owner, on GitHub and in 1Password)

- [x] 2.1 Owner: decide design D1 (new `troupe-run-board` App, or the infrastructure App) and record it in design.md
      as "(owner, <date>)". Verify that design.md's D1 no longer says OPEN QUESTION. Done: option A, a new App
      (owner, 2026-10-18), and D1 says so
- [x] 2.2 Owner: create the GitHub App `troupe-run-board` in the troupe-run org, installable only on this account,
      with the webhook off. Organisation permission: Projects read and write. No repository permissions beyond the
      metadata GitHub always grants. Install it on `troupe-run/website` only. Verify with
      `gh api orgs/troupe-run/installations --jq '.installations[] | select(.app_slug=="troupe-run-board") | {permissions, repository_selection}'`,
      which should show `organization_projects: write`, `metadata: read` and `selected`. Found (2026-10-18): App ID
      5367918, installation 172676444, `organization_projects: write` and `selected`. GitHub lists no `metadata` for
      an App with no repository permissions. The token's own `GET /installation/repositories` (3.2) returned `[]`:
      it covers no repository, which works, and the owner chose to keep it that way (design D1, 2026-10-18)
- [x] 2.3 Owner: generate a private key, store it in 1Password as `troupe-run-board`, field `private key`, in vault
      `troupe.run`, and delete the downloaded file. Verify that
      `op read -n "op://troupe.run/troupe-run-board/private key" | head -c 31` prints only the PEM header. Found: an SSH Key item, header `-----BEGIN RSA PRIVATE KEY-----`, as for the release
      App
- [x] 2.4 Record the App's ID and client ID on #59. Verify the comment exists. Done: #59 issuecomment-6249415918, with bot user ID 344329069

## 3. Probe the token (design D6)

- [x] 3.1 Owner: create a throwaway org project (for example "infra-probe board") and a `troupe-run/infra-probe-*`
      repository with one issue. Verify both exist with `gh project list --owner troupe-run` and `gh issue list -R <probe>`
- [x] 3.2 Mint an installation token locally from the 1Password key, without printing it. Use it to run
      `gh project item-add <probe-project> --owner troupe-run --url <probe issue>`. Record in design.md D6 whether it
      succeeds without the App being installed on the probe repository (question 1), and whether gh accepts the
      token (question 2). Verify the item shows in `gh project item-list <probe-project> --owner troupe-run`. Done:
      both yes, and the item showed on project 3 (design D6, Findings)
- [x] 3.3 With the same token, try `gh issue comment` on a website issue. Verify that it's refused (question 3) and
      record that in D6. Done, without a live write: an invalid label write on website gave 403 (design D6)
- [x] 3.4 If 3.2 needed a repository permission, the owner adds "Issues: read" to the App and accepts it on the
      installation. Update the spec's permission line to match. Verify that 3.2 then succeeds, and that
      `openspec validate add-link-issue-to-board --strict` passes. Not needed: 3.2 succeeded with no repository
      permission
- [ ] 3.5 Owner: delete the probe project and the probe repository. Verify both are gone (404 / not listed)

## 4. The declarations that name the App

- [x] 4.1 Add `troupe-run-board` to `oob/app-installations.json` with the permissions found in group 3 and
      `repository_selection: selected` (design D4). Verify `uv run scripts/oob.py` reports no difference for App
      installations, where before this edit it reported the new App
- [x] 4.2 Add `BOARD_APP_CLIENT_ID` to `tofu/board.tf`, holding the client ID from 2.4, as a `github_actions_variable`
      on `module.repo_website`. Verify `uv run scripts/check.py` passes
- [x] 4.3 Document the steps done by hand in `oob/README.md` (design D4): a "website's board App (set up by hand)"
      section with creating and installing the App, storing and setting the key, checking it by name, and rotating
      it. Add a row for `troupe-run-board` with none (design D1) in the table of repositories, confirmed by the owner with
      the date. Verify the documented `gh api` check commands run as written

## 5. The plan

- [ ] 5.1 Open the pull request (`Closes #59`) and get CI's plan. Verify the plan creates only the `board` environment,
      its deployment policy and `BOARD_APP_CLIENT_ID` on website, changes no ruleset, and touches no secret

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`).
- After the merge and CI's apply (these can't be ticked before archive, so they're not tracked tasks):
  - Owner: set the secret with
    `op read -n "op://troupe.run/troupe-run-board/private key" | gh secret set BOARD_APP_PRIVATE_KEY --env board -R troupe-run/website`,
    and check it by name: `gh api repos/troupe-run/website/environments/board/secrets --jq '.secrets[].name'` prints
    `BOARD_APP_PRIVATE_KEY`.
  - Open an issue in troupe-run/website, on the troupe roadmap board, for the follow-up workflow change in design D5
    (a separate job holding the `board` environment, then `gh project item-add`).
- After the merge, comment on #59 with the PR and the archived change, and check the card says Done.
