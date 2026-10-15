# Tasks

## 1. Probe delete-on-merge without the deletion rule

- [x] 1.1 Remove `deletion = true` from the probe's copy of the ruleset in `tofu/probe/main.tf` and update its comment
      (design D2, D3). Verify with `tofu fmt -check` and `tofu validate` on `tofu/probe`
- [x] 1.2 Owner: create a throwaway `troupe-run/infra-probe-<date>` with delete-on-merge on, and add it to the
      infrastructure App's installation. Run D3's steps 1–6 through `tofu/probe`, with the owner's own pushes and
      merge. Verify each step's outcome as D3 states it, with the GitHub output quoted. If step 4 keeps the branch,
      stop and ask the owner before going on
- [x] 1.3 Record the findings in design.md under D3, then unset the toggles, delete the probe repository and remove
      the probe's local state. Verify with `gh repo view troupe-run/infra-probe-<date>`, which reports not found, and
      `git status`, which shows no probe state

## 2. The release exemption drops the author check

- [x] 2.1 Pin what must keep applying on a release branch in troupe before the change (design D6, differential rule).
      With the current bot-authored setup, add the delivered-file case: a commit changing a file listed in
      `.github/guard-delivery.json` fails `delivered-file`. Verify it and the existing message and force-push cases
      pass on the current code, with `uv run pytest scripts/tests/test_guard_push_and_ci.py`
- [x] 2.2 Rewrite the release-please section's tests per design D6's table, each named for what its body checks, with
      an ordinary author and no monkeypatched address. Delete the four tests D6 lists for removal, and switch the
      `--repository` tests to an ordinary author. Verify the "Any author" and ordinary-author cases fail on the
      current code only on `commit-branch-change`
- [x] 2.3 Extend `release_ruleset_repositories` to require `creation = true` and `update = true` in the ruleset block,
      and add a removal test with `creation = false` in a copy of the file (design D6). Verify both tests pass
      against the real `tofu/release.tf`, that the new one fails if the check is removed, and that the old one still
      passes
- [x] 2.4 In `scripts/guard.py`:
      - replace `release_branch_by_the_bot` with `reserved_release_branch(branch, repository)`, a check of the name
        and `RELEASE_REPOSITORIES`;
      - remove `RELEASE_AUTHOR_EMAIL`;
      - reword `RELEASE_REPOSITORIES`'s docstring and `run_ci`'s, citing D1 and #47 (design D1).

      Verify all of `scripts/tests/` passes, and `uv run scripts/check.py` passes

## 3. The ruleset allows deletion

- [x] 3.1 Remove `deletion = true` from `github_repository_ruleset.release_branches` in `tofu/release.tf`, and reword
      its comment: it reserves creation and update so the name is proof on troupe, and allows deletion so
      delete-on-merge removes the branch (design D2). Verify that `uv run scripts/check.py` passes (fmt, validate
      and 2.3's coverage tests)
- [x] 3.2 Reword README's "release branches" paragraph and its `tofu/release.tf` table row (design D5). Verify with
      `grep -rn "RELEASE_AUTHOR_EMAIL\|delete-on-merge\|authored every commit" README.md docs scripts tofu`, which
      should match nothing stale

## 4. The principle is written down

- [x] 4.1 In `docs/development-workflow.md`:
      - add D5's principle paragraph at the head of Known gaps;
      - rewrite the forged-delivery entry and the release-exemption entry;
      - update the `commit-branch-change` row of the rules table to say that on GitHub, a `release-please--` branch
        in troupe is exempt by its name.

      Verify `uv run pytest scripts/tests/test_guard_docs.py` passes
- [x] 4.2 Reword README's delivery bullet on forged authors and `.github/workflows/tofu.yml`'s header comment as drift
      detection (design D5). Verify with `grep -rn -i "forg" README.md .github docs` that each remaining mention
      describes the check as catching mistakes, not forgery
- [x] 4.3 Add one constraint to `openspec/config.yaml`'s context stating the principle, and cite #47. Verify that
      `openspec validate drop-forgery-resistance --strict` passes and that the `context` of
      `openspec instructions apply --change drop-forgery-resistance --json` shows the line (`openspec context --json`
      doesn't return the config's context)

## 5. Evidence

- [x] 5.1 Run `uv run scripts/check.py` on the branch head and record that it passes
      Done 2026-10-15 on `38410cf`: `check: all gates passed`, 679 tests
- [x] 5.2 Fast-forward onto `origin/main`, then run a local plan. Verify it shows exactly two changes (design D4):
      - the in-place update of troupe's "release branches" ruleset, dropping `deletion`;
      - the update of troupe's `scripts/guard.py`.

      Record the summary in the change

      Done 2026-10-15 on `38410cf`, level with `origin/main` (its state commit included): `Plan: 0 to add, 2 to
      change, 0 to destroy.` The changes are `github_repository_file.guard["troupe:scripts/guard.py"]` updated in
      place (`875ae341dab2` -> `9e73796813c2`), and `github_repository_ruleset.release_branches` (id 25004049) updated
      in place with `- deletion = true -> null`, the rest unchanged

## Workflow follow-up

- Open the pull request with `Closes #47`. The owner approves the `plan-pr` run, and the posted plan matches 5.2.
- Archive on the branch. The owner merges by rebase.
- After the owner approves the apply, verify:
  - troupe's ruleset has `creation` and `update` and no `deletion`;
  - troupe's `scripts/guard.py` matches this repository's;
  - troupe's `guard` and CI pass on the delivery commit.
- Comment on #47 with the PR and the archived change, close it if the PR didn't, and check its card is Done.
- On troupe's next release, check that the release branch was deleted on merge, and that release-please created it
  again for the release after.
