# Tasks

## 1. Prove the provider's behaviour on a throwaway repository (D3)

- [ ] 1.1 Re-read the live milestones of all four managed repositories
      (`gh api "repos/troupe-run/<repo>/milestones?state=all"`). Verify they still match design.md's Context: troupe
      has only milestone 1, `alpha-0`, open, with 3 closed issues, and the others have none. If anything differs,
      stop and update the design first
- [ ] 1.2 On a throwaway repository with one milestone holding one issue, verify with a scratch OpenTofu config (not
      this repository's state): (a) the milestone imports with ID `<owner>/<repository>/<number>`; (b) changing its
      declared title plans as an in-place update, and after the apply the milestone keeps its number and its issue;
      (c) renaming it by hand on GitHub shows as a title change in the next plan; (d) removing it from a
      `for_each` with `prevent_destroy = true` fails the plan. Record each result here. If (b) is a replacement, stop
      and take it back to the owner (design D3). Delete the throwaway repository afterwards and verify it's gone

## 2. Declare the milestones and adopt alpha-0 (D1, D2, D3)

- [ ] 2.1 Add `tofu/milestones.json` with the four repositories and the three milestones, using D2's descriptions, and
      a `_comment` (or the README) saying a key is never changed. Add `tofu/milestones.tf`: a local read with
      `jsondecode`, and `github_repository_milestone.release` over each (repository, key) pair, addressed
      `"<repository>/<key>"`, with `lifecycle { prevent_destroy = true }` and a header citing spec: milestones and #68.
      Add the `import` block for troupe's milestone 1 to `tofu/imports.tf`. Verify `uv run scripts/check.py` passes
      (`tofu fmt -check`, `tofu validate`)
- [ ] 2.2 Add a `tofu/milestones.json` / `milestones.tf` row to README.md's Layout table, saying what they hold, that
      a finished release is closed by state, never removed, and that a key never changes. Verify
      `uv run scripts/check.py` passes
- [ ] 2.3 Fast-forward onto `origin/main`, then run a local plan. Verify its summary is
      `Plan: 1 to import, 11 to add, 1 to change, 0 to destroy.`, where the one change is troupe's milestone 1's title,
      `alpha-0` to `0.1.0`, and nothing else. Record the summary here. If it shows anything else, fix the declaration
      and re-plan before going on
- [ ] 2.4 Commit (`feat(tofu): declare the release milestones in every managed repository`)

## 3. check.py keeps the declaration honest (D4)

- [ ] 3.1 Add a test that the repositories in `milestones.json` equal the names of the `module "repo_*"` calls in
      `tofu/repositories.tf`. Verify it fails, naming the repository and the file, when a repository is removed from
      the list in a temporary copy, then passes on the real files
- [ ] 3.2 Add a test that keys and titles are unique and each state is `open` or `closed`. Verify it fails on a
      duplicate title and on state `done`, each naming the milestone and the problem, then passes on the real file
- [ ] 3.3 Commit (`test: keep the milestone declaration in step with the managed repositories`). Verify
      `uv run scripts/check.py` passes before the commit

## 4. oob.py reports a milestone made by hand (D5)

- [ ] 4.1 Add the milestones check to `scripts/oob.py`, reading the repositories and titles from
      `tofu/milestones.json`, and update `oob/README.md`'s list of what it checks. Add tests in
      `scripts/tests/test_oob.py`: an undeclared title on one repository is reported, naming the repository, the title
      and `tofu/milestones.json`; a declared set reports nothing; a closed undeclared milestone is reported too; an
      unreadable repository raises `UnreadableError`. Verify the tests pass and `uv run scripts/check.py` passes
- [ ] 4.2 Run `uv run scripts/oob.py` against GitHub. Before the apply, verify it reports exactly troupe's `alpha-0`
      as undeclared and nothing else new. Record the output here
- [ ] 4.3 Commit (`feat(oob): report a milestone that isn't declared`)

## 5. Pull request

- [ ] 5.1 Open the pull request with `Closes #68`, the D3 plan summary, and a note that the apply renames alpha-0.
      Verify CI is green on every job and its plan (once the owner approves that run) shows the summary from 2.3

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- After the owner approves the apply: verify each managed repository has 0.1.0, 0.2.0 and 1.0.0 open, with the
  declared descriptions, and that troupe's 0.1.0 is milestone 1 with its 3 issues. Verify `prevent_destroy` now holds
  (a local plan with one milestone removed from the declaration fails), then restore it. Run `uv run scripts/oob.py`
  and verify it reports no milestone differences.
- Sweep the issues into the milestones, as the owner agreed on 2026-10-17: every closed issue in troupe,
  infrastructure and website goes to 0.1.0; the open issues as listed on #68. Record the sweep on #68.
- Comment on #68 with the PR and the archived change, then check that it's closed and its card says Done.
