# Tasks

## 1. The owner's steps on GitHub (design D3, D5)

Troupe's discussions are not turned on here: that's task 7.1, immediately before the merge (design D3).

- [x] 1.1 Ask the owner to set private vulnerability reporting to `enabled` in the "troupe-run baseline" code
  security configuration (design D4), and change `oob/code-security.json` to match. Verify
  `gh api repos/troupe-run/<repo>/private-vulnerability-reporting` returns `{"enabled":true}` for all four, and
  `uv run scripts/oob.py` reports no difference for code security or private vulnerability reporting.
- [x] 1.2 Ask the owner to run `gh project link 1 --owner troupe-run --repo troupe-run/infrastructure`. Verify the
  `projects` GraphQL read in `scripts/oob.py` lists `infrastructure` for project 1, then add it to
  `oob/projects.json`.
- [x] 1.3 Check whether CI's drift token can read the new checks without Discussions: read: mint a token as
  `tofu.yml`'s drift job does (same App, repositories and permissions) and read troupe's and a public repository's
  categories, `.github`'s features and a repository's reporting. Done 2026-10-29: every read worked, so the App gains
  no permission and `oob/app-installations.json` is unchanged (design D5).

- [x] 1.4 Create an `infra-probe-*` repository, turn its pull requests off, and commit a file to it through the
  contents API (`gh api -X PUT repos/troupe-run/<probe>/contents/<file>`), as the App writes `.github`'s files.
  Verify the commit lands on `main`, record the result in design D4a, then delete the probe repository.
- [ ] 1.5 If 1.4 passed, ask the owner to turn pull requests off in `.github`. Verify
  `gh api graphql` reads `hasPullRequestsEnabled: false` for `.github`.

## 2. Repository features in the module (design D1, D2)

- [x] 2.1 Add `has_discussions` (default `false`), `has_issues` (default `true`) and `actions_enabled` (default
  `true`) to `tofu/modules/repository/variables.tf`, and use the first two in `github_repository.this` in place of
  the hard-coded values. Verify `tofu fmt -check` and `tofu validate` pass.
- [x] 2.2 Add `github_actions_repository_permissions.this` to the module (`enabled = var.actions_enabled`,
  `allowed_actions` `"all"` when on, `sha_pinning_required = false`), with a comment citing design D2. Verify
  `tofu validate` passes.
- [x] 2.3 In `tofu/repositories.tf`, set `has_discussions = true` on troupe, `has_issues = false` and
  `actions_enabled = false` on `.github`, and `has_projects = true` on infrastructure, each with a comment saying why.
  Verify `tofu validate` passes.
- [x] 2.4 Add four `import` blocks in `tofu/imports.tf` adopting each repository's Actions settings by name. Verify
  a local plan imports all four, with no change for troupe, infrastructure and website (if `allowed_actions` plans a
  change on `.github`, settle it as design D2 says, and record which).

## 3. Out-of-band checks (design D4, D5, D9)

- [x] 3.1 Add `oob/private-vulnerability-reporting.json` (all four repositories, `enabled: true`) and a check in
  `scripts/oob.py` that reads each repository's setting, reports one that's off, and treats a refused read as an
  error naming the repository. Add tests to `scripts/tests/test_oob.py` for match, off, missing repository and a
  refused read, each failing when its behaviour breaks. Verify `uv run pytest scripts/tests/test_oob.py` passes.
- [x] 3.1a Add `oob/repository-features.json` (`hasPullRequestsEnabled` false for `.github` only,
  `hasSponsorshipsEnabled` false everywhere) and a check reading each declared repository through GraphQL. Add tests
  for match, pull requests turned on in `.github`, Sponsorships turned on, and a refused read naming the repository.
  Verify the tests pass and `uv run scripts/oob.py` reads all four.
- [x] 3.2 Add `oob/discussion-categories.json` (Q&A, Ideas, Announcements: `name`, `slug`, `isAnswerable`) and a
  `Check` reading troupe's categories through GraphQL. Add tests for match, a category added by hand, discussions
  off (no categories), and a refused read. Verify the tests pass and `uv run scripts/oob.py` reads the categories,
  reporting only the three as missing while troupe's discussions are off (until 7.1).
- [x] 3.3 Add rows for both files to `oob/README.md`'s table, and a "Not managed" section listing the home page's
  Releases, Packages and Deployments panels, forking on a public repository, and a category's
  announcement-only format, each with why. Verify the README's checks in `uv run scripts/check.py` pass.

## 4. Org Pages settings (design D8)

- [x] 4.1 Set `members_can_create_pages`, `members_can_create_public_pages` and `members_can_create_private_pages` to
  `false` in `tofu/org.tf`, with a comment citing design D8. Verify `tofu validate` passes and the plan shows only
  those three changing on the org.

## 5. Questions go to troupe's discussions (design D7)

- [x] 5.1 Add the "Ask a question" contact link to `org-profile/.github/ISSUE_TEMPLATE/config.yml`. Verify
  `uv run pytest scripts/tests/test_org_profile.py` passes and the file parses as YAML.
- [x] 5.2 Add a "Questions" section to `org-profile/CONTRIBUTING.md`, before "How work flows", pointing to troupe's
  discussions. Verify `uv run pytest scripts/tests/test_org_profile.py` passes.

## 6. Evidence before the pull request

- [x] 6.1 Run `uv run scripts/check.py` and confirm it passes.
- [x] 6.2 Run a local plan against current state (fast-forwarded onto `origin/main`) and confirm it shows only: four
  Actions imports, `.github`'s issues and Actions off, infrastructure's projects on, the three org Pages settings, and
  the two `.github` file updates. Quote it in the pull request. (Run 2026-10-29 on `9e7f179`: 4 to import, 7 to
  change, 0 to destroy. It also showed troupe's `has_discussions` false → true, which stays in the plan until 7.1
  turns discussions on by hand.)
- [ ] 6.3 Run `uv run scripts/oob.py` and confirm its only differences are the three discussion categories missing
  from troupe (discussions are still off until 7.1), with the new checks among those it ran. Quote it in the pull
  request.

## 7. Immediately before the merge (design D3)

This group is done after review and archive, as the last thing before the owner merges. Until the merge, every plan
of `main` shows troupe's discussions turning back off, so the window is kept to minutes.

- [ ] 7.1 Ask the owner to turn discussions on in troupe and trim its categories to Q&A, Ideas and Announcements
  (Announcements announcement-only), then merge. Verify with `gh api graphql` (`repository(owner:"troupe-run",
  name:"troupe") { hasDiscussionsEnabled discussionCategories(first:20) { nodes { name slug isAnswerable } } }`):
  discussions on, exactly those three, only Q&A answerable; and `uv run scripts/oob.py` reports no differences.
- [ ] 7.2 Before the merge lands, check that no apply of `main` is waiting for approval; if one is, tell the owner its
  plan turns troupe's discussions off, so they don't approve it until this change's apply.

## Workflow follow-up

- After the apply, open infrastructure's new-issue page and confirm it offers the Feature, Bug and Decision forms and
  "Ask a question" (design D6). If the forms are gone, open a pull request setting `.github`'s `has_issues` back to
  `true` and raise it with the owner.
- After the apply, re-run the website's deploy on `main` and confirm https://troupe.run serves it, and that the next
  plan shows no change to `github_repository_pages` (design D8). If either fails, revert the Pages settings by pull
  request and raise it with the owner.
- Confirm the drift job of the next plan of `main` is green.
- Comment on #136 with the pull request and the archived change, and check its roadmap card says Done.
