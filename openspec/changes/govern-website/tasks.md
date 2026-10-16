# Tasks

## 1. Before anything is planned

- [x] 1.1 Ask the owner whether the website's existing history is rewritten (design D7). Record the answer and its
      date here, and on #54. If it's yes, the owner's break-glass rewrite is done and verified (`git log --format=%s`
      on the website's `main` shows only Conventional Commits, its "Last updated" dates are unchanged on a docs
      page, and a plan shows no ruleset drift once `protect main` is restored) before 1.2 starts
      Done 2026-10-16: no rewrite (design D7). The owner also decided how outside "Improve this page" pull requests
      are handled: a maintainer carries them (design D8). Both recorded on #54
- [x] 1.2 Open the website's bootstrap issue in `troupe-run/website` with `--project "troupe roadmap"`, describing
      design D1's contents, including D8's CONTRIBUTING text for outside fixes, and linking #54. Verify it's on the board with
      `gh issue view <n> -R troupe-run/website --json projectItems`
      Done 2026-10-16: troupe-run/website#7, on "troupe roadmap" (Todo)
- [x] 1.3 Check that the website's bootstrap pull request (D1) is merged. Its `main` holds `openspec/`,
      `scripts/check.py`, `scripts/check-paths.toml` (skipping at least `openspec/**`), CONTRIBUTING.md (with D8's
      text on outside fixes) and CLAUDE.md, and none of the delivered paths. The CI job is still named `test` and runs `uv run scripts/check.py`.
      Verify with `gh api repos/troupe-run/website/contents/<path>` for each, a 404 for each delivered path, and the
      full check's macOS time recorded in that pull request, under the guard's 10-minute limit
      Done 2026-10-16: website#7 closed by website#14 (merged 11:14 UTC, change `adopt-org-workflow` archived on its
      branch). On `main`: `openspec/config.yaml`, `scripts/check.py`, `scripts/check-paths.toml` (skips `openspec/**`,
      `.claude/**`, `docs/**` and the contributor docs), CONTRIBUTING.md with D8's text, and CLAUDE.md. All eight
      delivered paths 404. CI's job is still `test` and runs `uv run scripts/check.py`. Full check on macOS: 38.3 s
- [x] 1.4 Owner: confirm that the infrastructure App's installation lists `website` in the App's settings
      (teams-and-access), and record that here
      Done 2026-10-16: the owner confirmed `website` is in the installation's repository list

## 2. The website receives the guard

- [x] 2.1 In `scripts/tests/test_required_checks.py`, add a test that reads `guard_targets` from
      `tofu/guard_delivery.tf` and checks that each repository it names requires `guard (workflow rules)` from
      `github-actions` in `tofu/required-checks.json` (design D3). Verify it passes on `main`'s data (troupe only).
      Then add `module.repo_website.name` to `guard_targets` on its own and verify the test fails, naming `website`
      Done 2026-10-16: 12 passed on main's data; with only `guard_targets` changed it failed with
      `{'website': ['guard (workflow rules)']}`. It replaces troupe's own guard-check test, which it generalises
- [x] 2.2 Add `{"context": "guard (workflow rules)", "app": "github-actions"}` to the `website` entry of
      `tofu/required-checks.json`, and leave DCO out (design D3). Update the module's comment if it names the
      checks. Verify the 2.1 test passes
      Done 2026-10-16: 12 passed
- [x] 2.3 In `tofu/guard_delivery.tf`, make `guard_targets` name both repositories, and make `depends_on` list
      `module.repo_troupe` and `module.repo_website` (design D2). Update the comments that assume troupe alone. In
      `tofu/repositories.tf`, give `repo_website` `app_bypass_id = local.infrastructure_app_id` and
      `has_projects = true`, each with a comment giving the reason, as `repo_troupe`'s do. Verify `tofu fmt -check` and
      `tofu validate` are clean
      Done 2026-10-16: `tofu fmt -check -recursive` clean; `tofu validate` passed in `check.py`
- [x] 2.4 Edit the `development-workflow` spec's Purpose in `openspec/specs/development-workflow/spec.md` so it names
      this repository, `troupe` and `website` (design D5). Verify `openspec validate --specs --strict` passes
      Done 2026-10-16: `openspec validate --specs --strict`: 11 passed, 0 failed
- [x] 2.5 Update README.md "Delivering the guard" and "To stop delivering" so they speak of each repository that
      receives the guard, and so the stop steps name that repository's `app_bypass_id` (design D5). Verify
      `uv run pytest scripts/tests/test_guard_docs.py` passes, and
      `grep -n "troupe" README.md` shows no remaining line that means "every governed repository"
      Done 2026-10-16: the grep leaves only lines about troupe's own matrix and release branches. README also
      gains "To add a repository". `test_guard_docs.py` passed in `uv run scripts/check.py` (all gates passed)

- [x] 2.6 Limit the guard files' `import` block in `tofu/imports.tf` to troupe, the only repository whose files were
      adopted. Added during apply: the first local plan failed with a 404 for each of the six adopted paths on the
      website, because the block imported them for every target. Verify `tofu fmt` and `tofu validate` pass and the
      plan creates all eight website files
      Done 2026-10-16 (preview plan, before 1.3): `Plan: 8 to add, 2 to change, 0 to destroy.` The eight
      `guard["website:…"]` files, `repo_website`'s `has_projects` false -> true, and its ruleset gaining the App
      (5272634) as a bypass actor and `guard (workflow rules)` (15368). Nothing for troupe, infrastructure or
      `.github`. 4.1 is still run again once the website has bootstrapped

## 3. The roadmap is linked and checked

- [x] 3.1 In `scripts/tests/test_oob.py`, add a test for the projects check: a declaration listing
      `["troupe", "website"]` against a GitHub answer linked only to `troupe` reports the difference and exits
      non-zero. Verify it fails before 3.2
      Done 2026-10-16: two tests. The drift report itself already worked, since the comparison handles any
      field, so that test passed before 3.2. The one that failed before 3.2 checks the query asks for and sorts the
      linked repositories; its name and docstring say it checks the query's text only
- [x] 3.2 Extend the `projects` check in `scripts/oob.py` to read each project's linked repositories in the same
      GraphQL query, sorted by name, and add `"repositories": ["troupe", "website"]` to `oob/projects.json` (design
      D4). Update `oob/README.md` to say the links are checked and how the owner makes one. Verify 3.1 passes and
      `uv run scripts/check.py` passes
      Done 2026-10-16: 23 passed in `test_oob.py`; `check.py` all gates passed (805 tests). Against GitHub,
      `oob.py` reports `projects: 1 repositories is ['troupe'] on GitHub, declared ['troupe', 'website']`, which
      3.3 resolves. Its other four lines are troupe label drift that predates this change
- [x] 3.3 Owner: run `gh project link 1 --owner troupe-run --repo troupe-run/website`. Verify `uv run scripts/oob.py`
      reports no difference, and record its output here
      Done 2026-10-16: the owner linked it. `oob.py` no longer reports `projects`. Its five remaining lines aren't this
      change's: the App's `pages: write` (from `website-pages`, which declares it) and the four troupe label lines

## 4. Plan and evidence

- [ ] 4.1 Fast-forward onto `origin/main` once its latest state commit has landed, then run a local plan. Verify
      it shows exactly design D2's changes: the website's ruleset updated in place (bypass actor and one required
      check), `repo_website`'s `has_projects` turned on, and eight `github_repository_file.guard["website:…"]`
      creations, with nothing for troupe, infrastructure or `.github`. Record the summary line
- [ ] 4.2 Push the branch and open the pull request (`Closes #54`). Verify `check`, every `guard tests` leg,
      `guard (workflow rules)` and DCO pass. Verify that the posted plan, once the owner has approved its run,
      matches 4.1, and attach `scripts/oob.py`'s output
- [ ] 4.3 Before the owner approves the plan, list open pull requests in `troupe-run/website`. Verify that none is
      open, or note each one that will need its `guard` check to run again after the apply (design, Risks)

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging. The owner merges by rebase and approves `main`'s `apply` job.
- After the apply, verify:
  - the website's `main` has eight `chore(guard): deliver …` commits by the App, each with green `guard` and CI runs;
  - `gh api repos/troupe-run/website/rulesets/<id>` lists the App as a bypass actor, and `test` and
    `guard (workflow rules)` as required checks;
  - a fresh plan shows no changes;
  - the website's next pull request reports `guard (workflow rules)` as required, and merges with no sign-off.
- Comment on #54 with the pull request and the archived change, check that it's closed, and set its card to Done.
  Do the same for the website's bootstrap issue, if its own pull request didn't close it.
- Remove this change's worktree and branch once it's merged and verified.
