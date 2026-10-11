# Tasks

## 1. Move the guard here unchanged (D1)

- [x] 1.1 Copy from `troupe-run/troupe` at `6099deb`, byte for byte:
  - `scripts/guard.py`;
  - `scripts/tests/conftest.py` and `test_guard_*.py`;
  - `docs/development-workflow.md`.

  Add whatever dev dependencies the tests need to `pyproject.toml`. Verify:
  - each file's sha256 matches troupe's at `6099deb`;
  - `uv run pytest scripts/tests` passes;
  - `scripts/check.py` passes.
- [x] 1.2 `scripts/check.py` turns the git hooks on (`activate_git_hooks`, as in troupe), with
  `test_check_activation.py` adapted to this repo's `check.py`. Verify: the test passes, and fails when activation is
  removed.
- [x] 1.3 Copy `.githooks/`, `.claude/settings.json` and `.github/workflows/guard.yml` byte for byte, and turn the
  hooks on here. Verify:
  - their sha256 values match troupe's;
  - the next commit on this branch runs the pre-commit check, shown in its output;
  - a commit attempted with a non-conventional message is refused by the `commit-msg` hook, and isn't made;
  - the `guard` check is green on the pushed branch.
- [x] 1.4 Add the `guard-tests` CI job (D10): macOS and Windows, plus 3.13 on Linux, running
  `scripts/tests/test_guard_*.py`. Verify: every job is green on the pushed branch.

## 2. Adopt troupe's copies (D9 step 2)

- [x] 2.1 Add `tofu/guard_delivery.tf`: a `github_repository_file` for each of troupe's six existing guard files, the
  matching import blocks, and `ignore_changes = [commit_message]` for now (group 4 removes it). Verify:
  - `scripts/check.py` passes;
  - the plan shows six imports and no other change.
- [ ] 2.2 Show the owner the saved adoption plan, then apply it and commit the state. Verify:
  - the owner approved it;
  - troupe gets no new commit (`gh api repos/troupe-run/troupe/commits?per_page=1` is unchanged);
  - the plan afterwards says "No changes".

## 3. Prove delivery on a probe (D8)

- [ ] 3.1 The owner grants the App Workflows write and accepts it on the installation. Record it in
  `oob/app-installations.json`. Verify: `scripts/oob.py` reports no differences.
- [ ] 3.2 Create `troupe-run/infra-probe-<date>`; the owner adds it to the App's installation. Extend `tofu/probe`
  with `delivery_bypass`, and deliver a script and `.github/workflows/guard.yml` to it with D3's commit messages.
  Verify:
  - with `delivery_bypass = false`, the delivery is refused, with the output recorded;
  - with it true, the delivery lands and is made by the App;
  - the owner's direct push is still refused;
  - the workflow file delivered without error.
- [ ] 3.3 D3's cases on the probe:
  - an unchanged plan is clean;
  - a content change makes exactly one commit with the new message;
  - a hand edit shows content and message drifting, and the apply restores both;
  - a message-only difference: record whether the provider makes a commit, and write the answer into D3.

  Verify: each output recorded.
- [ ] 3.4 With `guard.py` and `guard.yml` delivered to the probe, check two things. A delivery push to `main` passes
  the `guard` check. A branch carrying a hand-made commit to a delivered file fails it, once group 4's rule exists
  (re-run this task after 4.2). Verify: both check runs' URLs and results recorded.
- [ ] 3.5 Delete the probe repo and its local state and files. Verify: `gh repo view` reports not found.

## 4. Generalise the guard and add the rule

- [ ] 4.1 Add the source note (D2) to every delivered source that can hold a comment. Generate
  `.github/guard-delivery.json` from the delivery list. Switch the delivery and `org_profile.tf` commit messages to
  D3's form, and remove `ignore_changes`. Verify:
  - `scripts/check.py` passes;
  - a local plan, not applied, shows only content and message changes to delivered and synced files, plus the
    new list.
- [ ] 4.2 Add the `delivered-file` rule (D4) to pre-commit, the edit hook and `guard.py ci`, with tests for each
  layer. Cover: refused in a receiving repository; allowed in the source; a commit by the App's bot accepted in CI.
  Verify: the tests pass, each one fails when its branch of the rule is removed, and the guard's tests pass on all
  three OSes in CI.
- [ ] 4.3 Reword the troupe-only text in `guard.py` (docstring, `WORKFLOW_SUMMARY`) and in
  `docs/development-workflow.md`:
  - "this repository" becomes "a governed repository";
  - the `delivered-file` row is added;
  - the "Known gaps" and the GitHub-check text are updated for this repo.

  Add a short `CLAUDE.md` here, and a link from `org-profile/CONTRIBUTING.md` to the rules doc. Verify:
  `test_guard_docs.py` passes, and `CONTRIBUTING.md` is the only `org-profile` change.
- [ ] 4.4 Add `delivery_bypass` to `modules/repository` (D5), set it on `repo_troupe`, and amend the "never direct
  commits" constraint in `openspec/config.yaml` to name this exception. Verify: `scripts/check.py` passes, and a
  local plan shows the bypass entry added to troupe's ruleset only.
- [ ] 4.5 Update `README.md`:
  - how the guard governs this repo;
  - how a delivery is made: only from a commit whose CI is green on all three OSes, as a plan the owner approves;
  - rollback (D9's migration plan).

  Verify: the README describes what the probe showed.

## 5. The matching troupe change (D9 step 5)

- [ ] 5.1 Open the troupe issue. It removes troupe's `development-workflow` spec, the guard's tests (keeping
  `test_check_activation.py`) and `docs/development-workflow.md`, and points `CLAUDE.md` at this repo's doc. Verify:
  the issue exists and links to #8.
- [ ] 5.2 The troupe change is made through troupe's own workflow (issue, OpenSpec change, PR) and merged by the
  owner. Verify:
  - troupe's `main` no longer has those files;
  - its CI is green;
  - the change is archived there.

## 6. Deliver to troupe

- [ ] 6.1 Save the live plan from a commit whose CI is green on all three OSes, and show it to the owner. It should
  contain:
  - troupe's ruleset gaining the App bypass;
  - updates to the six delivered files;
  - the new `.github/guard-delivery.json`;
  - `.github`'s `CONTRIBUTING.md` and the synced files' messages.

  Verify: the owner approves it.
- [ ] 6.2 Apply the saved plan, and commit the state. Verify:
  - the plan afterwards says "No changes";
  - each delivered file in troupe matches its source's sha256;
  - troupe's `guard` and CI runs on the delivery pushes are green;
  - `scripts/oob.py` reports no differences.
- [ ] 6.3 In a scratch clone of troupe, check the delivered rule locally:
  - a commit changing `scripts/guard.py` is refused with `delivered-file`;
  - a commit on a change's branch that touches only other files is accepted.

  Nothing is pushed. Verify: both outputs recorded.

## 7. Pull request

- [ ] 7.1 Open the PR closing #8, with the probe, plan and apply evidence. Verify:
  - CI, `guard` and DCO are green;
  - the PR merges by rebase.

## Workflow follow-up

- Archive the change on the branch; the owner merges by rebase.
- Comment on #8, and tick `development-workflow` on #1.
