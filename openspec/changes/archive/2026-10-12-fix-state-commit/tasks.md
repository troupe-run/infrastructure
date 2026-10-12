# Tasks

## 1. The script and its tests (D1, D2)

- [x] 1.1 Add `scripts/commit_state.py` as in D1: standard library only, with I/O injectable for tests. Verify:
  - `scripts/check.py` passes, including ruff and `mypy --strict`;
  - `--help` names every argument.
- [x] 1.2 Add `scripts/tests/test_commit_state.py` with the D2 unit tests and the 300 KB end-to-end test. Verify:
  - the tests pass;
  - each fails when its behaviour is broken: blob ID, skip, the planned `sha`, the message, and the 409 exit;
  - the end-to-end test fails when the script is replaced by the old `jq --arg` command on Linux, or, where it can't
    be run on macOS, the CI `check` job's output is shown.
- [x] 1.3 Replace the "Commit the state to main as the App" step in `tofu.yml` with a call to the script; nothing else
  in the workflow changes. Verify: `actionlint` is clean, and the diff of `tofu.yml` touches only that step.

## 2. Prove it against GitHub (D3)

- [x] 2.1 On a throwaway repository, run the three cases of D3 with the owner's `gh` token. Verify:
  - the 300 KB file on GitHub is byte-identical (its blob SHA equals `git hash-object` of the local file);
  - the stale run exits 1 with a 409;
  - the unchanged run makes no commit (the commit count is the same before and after).
- [x] 2.2 Delete the throwaway repository and its clone. Verify: `gh repo list troupe-run` doesn't list it.

## 3. Recover the state and land it (D4)

- [x] 3.1 Copy the `state-after-apply` artifact of run 38200444558 over `tofu/terraform.tfstate`, and commit it.
  Verify: it's serial 7, of the same lineage, and still encrypted; and a local plan reports no changes.
- [x] 3.2 Open the pull request (`Closes #11`). Verify:
  - every check is green;
  - after the owner approves the PR plan, its comment reports no changes.

## Workflow follow-up

- Archive on the branch, syncing the `ci-apply` delta.
- After the owner merges:
  - the `main` run reports no changes and asks for no approval;
  - `main`'s state is serial 7.
- Comment on and close #11 and #6, and tick `ci-apply` on #1.
- The first real CI apply afterwards (`required-checks`) is the end-to-end proof of the state commit. Check that its
  state commit lands.
