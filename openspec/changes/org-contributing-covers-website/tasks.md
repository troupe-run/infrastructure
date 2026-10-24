# Tasks

## 0. infrastructure's licence

- [ ] 0.1 Copy troupe's `LICENSE` to the repository root, as design D4 says. Verify
      `gh api repos/troupe-run/troupe/contents/LICENSE --jq .content | base64 -d | diff - LICENSE` prints nothing
- [ ] 0.2 Add `license = "Apache-2.0"` and `license-files = ["LICENSE"]` to `pyproject.toml`'s `[project]`. Verify
      `uv lock --check` passes and `git diff uv.lock` is empty
- [ ] 0.3 Add design D4's `## Licence` section to the end of `README.md`. Verify it links `LICENSE`, names Apache-2.0
      and carries the trademark note, and that `uv run scripts/check.py` passes

## 1. The sign-off table and its test

- [ ] 1.1 Add the test of design D3 to `scripts/tests/test_org_profile.py`, with its fixture tests (missing row, DCO
      where it isn't required, None where it is, a licence other than `pyproject.toml`'s), and run it against the
      current guide. Verify the fixture tests pass and the real-guide test fails, naming every governed repository as
      having no row
- [ ] 1.2 Rewrite "Licence and sign-off" in `org-profile/CONTRIBUTING.md` as design D1 says. Verify the real-guide
      test now passes, that changing website's row to `DCO` makes it fail naming website, and that changing
      infrastructure's licence to `MIT` makes it fail naming both licences (revert both)

## 2. The rest of the guide

- [ ] 2.1 Make design D2's edits: the opening, the "A fix from outside" section, and the two additions to "How work
      flows". Verify `grep -n "has its own" org-profile/CONTRIBUTING.md` finds nothing, the guide names
      `Co-authored-by:` and Conventional Commits, the source note is still the first line, and `git diff` leaves the
      Milestones, Guardrails, pull request and Security sections unchanged
- [ ] 2.2 Run `uv run scripts/check.py` and `openspec validate org-contributing-covers-website --strict`, and verify
      both pass

## 3. Verify the plan

- [ ] 3.1 Once the owner approves the pull request's `plan-pr` run, read its plan comment and verify it reads
      `0 to add, 1 to change, 0 to destroy`, the one change being `github_repository_file.org_profile["CONTRIBUTING.md"]`.
      If it shows anything else, stop and find out why. Tick this in the same push as the archive, rebased onto
      `main`'s state commit, so the owner approves one more run

## Workflow follow-up

- Open the pull request with `Closes #120`. Its plan comment is 3.1's evidence. Before the second `plan-pr` approval,
  archive the change and rebase onto `main`'s state commit in one push.
- The owner merges by rebase, then approves the `apply` job of `main`'s plan. Verify
  `gh api repos/troupe-run/.github/contents/CONTRIBUTING.md --jq .content | base64 -d` matches
  `org-profile/CONTRIBUTING.md`, and its links work on GitHub. Verify
  `gh api repos/troupe-run/infrastructure/license --jq .license.spdx_id` prints `Apache-2.0`.
- Comment on #120 with the pull request and the archived change, check it's closed and its card is Done, and tell
  troupe-run/website#31 it's unblocked.
