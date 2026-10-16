# Tasks

## 1. What GitHub does with a mode commit

- [x] 1.1 On a throwaway repository in troupe-run, set up a `main` ruleset that the App bypasses, as on `website`.
      The App's installation is for selected repositories, so ask the owner to add the throwaway to it. Then:
      - create a `100644` file through the Contents API, as `github_repository_file` does;
      - as the App, make a Git Data API commit that sets it to `100755` (tree on the head's tree with the same blob,
        a commit with no author, and a non-forced ref update);
      - update the file's content through the Contents API.

      Verify and record here: the ref update is accepted, the commit's author is the App's bot, the mode is still
      `100755` after the content update, and a ref update on a stale head gets a 422 (design D4, Risks). Then delete
      the throwaway, and ask the owner to remove it from the installation
      Done 2026-10-17 on `troupe-run/throwaway-hook-modes`. The owner created it, added it to the App's installation,
      and added a "protect main" ruleset with the App bypassing `always`. GitHub refuses that bypass until the App is
      installed on the repository (422 "Actor ... must be part of the ruleset source or owner organization"). A
      probe ran as the App (a token minted for that repository only, with contents write) and used the real
      `hook_modes.apply_modes`:
      1. the Contents API created `.githooks/pre-push` as `100644`;
      2. `apply_modes` exited 0, and the file became `100755` (commit ae87bf8);
      3. the commit's author is `340938853+troupe-run-infrastructure[bot]@users.noreply.github.com` (the guard's
         `DELIVERY_AUTHOR_EMAIL`), login `troupe-run-infrastructure[bot]`, `verified: true`, message
         `chore(guard): set the mode of .githooks/pre-push from troupe-run/infrastructure`;
      4. a Contents API content update returned 200, and the mode stayed `100755`;
      5. a non-forced ref update from a stale head got 422 "Update is not a fast forward".

      Deleting the repository is left to the owner, since the guard reserves it (`owner-only`); deleting it also
      removes it from the installation
- [x] 1.2 In the same throwaway, point a scratch `github_repository_file` at the file (a local, throwaway state,
      never this repository's). Verify a plan after the mode commit shows no change, and record whether `commit_sha`
      moved (design, Risks)
      Done 2026-10-17, with a scratch configuration and plain local state outside this repository. Importing the file
      (ID `throwaway-hook-modes:.githooks/pre-push:main`) planned `no-op` with importing, and was applied to the
      scratch state only. `commit_sha` was 50cce88. Two mode commits followed through `apply_modes`, to `100644`
      (cdeb287) and back to `100755` (1623c9e). The next plan exited 0 ("No changes"), and after a refresh-only apply
      `commit_sha` was still 50cce88: the provider doesn't see a mode commit

## 2. The mode check reads the plan

- [x] 2.1 Add `scripts/hook_modes.py` with a `plan` command (design D1, D2). It reads `tofu show -json` of a saved
      plan for the `github_repository_file.guard` instances, gets each source's mode from `git ls-files -s`, reads
      each target's tree once with an injectable fetch, and writes `mode-plan.json` plus a Markdown summary. A
      truncated tree or an unknown mode is an error naming the repository. Standard library only, `mypy --strict`
      and ruff clean. Verify with tests in `scripts/tests/test_hook_modes.py`, each named for what it checks:
      - a `100644` target with a `100755` source is listed;
      - a matching mode isn't;
      - an absent file with an executable source is listed (D5);
      - a `100644` source is never listed;
      - the blob is git's hash of the content (checked against `git hash-object`);
      - a truncated tree refuses.

      Done 2026-10-17: `test_hook_modes.py` covers each case, plus a regular source never listed, an executable
      target with a regular source listed back to `100644`, a symlink mode refusing, one tree read per target, a
      delivery with unknown content refusing, and this repository's hooks being `100755`. 24 passed; ruff and
      `mypy --strict` clean. The plan JSON's shape is checked against a real saved plan in 5.2's first live plan
- [x] 2.2 Tag the new tests and script in `scripts/check-paths.toml` as its rules require. Verify
      `uv run scripts/check.py` passes, with the `guard_pytest` tag check included
      Done 2026-10-17: nothing to tag. `check-paths.toml` lists only `openspec/**` as skipped, so the new script and
      tests need the full check, which is the default. `uv run scripts/check.py`: 845 passed, all gates passed

## 3. The fix sets modes as the App

- [x] 3.1 Add an `apply` command to `scripts/hook_modes.py` (design D4). It reads `mode-plan.json` and, per repository,
      reads `main`'s head, refuses a listed file whose blob differs, creates the tree and commit with the message
      `chore(guard): set the mode of <paths> from troupe-run/infrastructure`, and updates the ref without force. It
      makes no request for an empty plan. Verify with offline tests using an injected HTTP layer:
      - one commit per repository, whose tree keeps every blob;
      - a changed blob refuses before any write and names the repository and the file;
      - a 422 on the ref update fails the run;
      - an empty plan makes no request;
      - the message is a Conventional Commit that the guard's own commit-message check accepts.

      Done 2026-10-17: each case is a test in `test_hook_modes.py`, plus a listed file missing at apply time
      refusing before any write, and exit codes 1 (refusal) and 2 (no token). Every check runs before any write, in
      every repository
- [x] 3.2 Document the command and its recovery in the script's docstring and in the README's apply section, and say
      in the break-glass section that a local apply doesn't set modes and the next CI plan does. Verify the guard's
      docs test (`test_guard_docs.py`) passes
      Done 2026-10-17: the docstring gives usage, design references and recovery. The README's "Changing the org"
      steps 2 and 3, "Break-glass", and "Delivering the guard" say how modes are planned and set, and that a local
      apply leaves them to the next CI plan. `test_guard_docs.py`: 2 passed

## 4. CI plans and applies modes

- [x] 4.1 In `.github/workflows/tofu.yml`, after the main plan:
      - run `hook_modes.py plan` with `GITHUB_TOKEN`;
      - set `changes` to true when OpenTofu has changes or the list isn't empty;
      - add the list to the run summary under the plan;
      - upload `mode-plan.json` with `main.tfplan`;
      - output the repositories to change (design D3).

      Do the same in the pull-request plan, posting the list in its comment. Verify `actionlint` (or the repo's
      workflow test, if one exists) and `uv run scripts/check.py` pass
      Done 2026-10-17: `actionlint` 1.7.12 (`uvx --from actionlint-py`) reports nothing, exit 0; `uv run
      scripts/check.py` passes, `test_required_checks.py`'s workflow checks included. Whether `GITHUB_TOKEN` can read
      the other repositories' trees is first shown by this pull request's own plan run
- [x] 4.2 In the apply job, add a step that runs only when `tofu apply` succeeded and the list isn't empty. It mints a
      token scoped to the plan's repositories with contents write, then runs `hook_modes.py apply`. Comment it with
      the design reference. Verify by reading the job's `if:` conditions against the ci-apply spec's scenarios, and
      quote them here
      Done 2026-10-17. The conditions:
      - job: `if: needs.plan.outputs.changes == 'true'`, where `changes` is
        `steps.plan.outputs.changes == 'true' || steps.modes.outputs.changes == 'true'`. A plan with neither still
        ends without asking for approval, and a mode-only plan waits in the `apply` environment, which only the owner
        approves.
      - both mode steps: `if: steps.apply.outcome == 'success' && needs.plan.outputs.mode_repositories != ''`. They
        run only after a successful apply. They're placed before the state steps, which keep
        `always() && steps.apply.outcome != 'skipped'`, so the state is still committed after a failed apply or a
        failed mode step.
      - the token has `repositories: ${{ needs.plan.outputs.mode_repositories }}` and `permission-contents: write`.
- [x] 4.3 Update `docs/development-workflow.md` and the guard-delivery section of the README to say that a delivered
      file keeps its source's mode, how the plan shows a difference, and that the App sets it after the apply. Verify
      `uv run scripts/check.py` passes
      Done 2026-10-17: `docs/development-workflow.md`'s guard-delivery section and the README's "Delivering the
      guard"; check passes (at the commit)

## 5. Activation reports a hook git skips

- [ ] 5.1 Extend `activate_hooks` in `scripts/guard.py` (design D6). Keep its `str | None` signature. Name each
      `.githooks/` file that isn't executable, with the wording for a delivered or a source file, and skip it where
      `os.name == "nt"`. Verify with tests in `test_guard_session.py` and `test_check_activation.py`:
      - a non-executable hook is reported at session start and by the check;
      - a delivered one names troupe-run/infrastructure;
      - a source one names `git update-index --chmod=+x`;
      - all-executable reports nothing;
      - the check's exit code is unchanged;
      - Windows reports nothing (simulated with a patched `os.name`).

      All of these pass on the three-OS CI matrix

## Workflow follow-up

- Open the pull request with `Closes #69`, and post the plan as evidence once the owner approves its run.
- Run `/opsx:archive` on the branch before merging. The owner merges by rebase.
- After the change's first apply on `main` (moved here from task 5.2, because the change is archived before it
  merges): check that `git ls-tree origin/main .githooks/` in `website` shows `100755` for all three hooks. Check
  that the App's commit is on `main` with a green `guard` run, and that the next plan shows no change in OpenTofu or
  in modes. Record the commit and the run on #69 (spec: "The approved apply sets the mode").
- After the merge and that check, comment on #69 with the PR and the archived change, check that it's closed, and set
  its card to Done.
- In a `website` clone, check that `git push` no longer prints the "hook was ignored" hint.
