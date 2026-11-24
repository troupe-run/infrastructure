# Tasks

## 1. Record the Purpose

- [x] 1.1 Read the `config-renames` Purpose through `scripts/oob.py`'s `purpose()` (from troupe#505's branch until it
      merges), and add it to `oob/troupe-spec-purposes.json` where design D1 says. Verify the keys are sorted, the
      entry matches #392's quote, and `git diff` shows only that added line (37 entries, sorted, #392's quote, one line added;
      between `config-hand-edits` and `docs-publishing`; read from `config-mv` at bdd8f124)
- [x] 1.2 Check the description of `cap:config` against the Purpose (design D2), and leave `tofu/labels/troupe.json`
      unchanged. Verify `git diff tofu/` is empty and `scripts/tests/test_labels.py` passes (empty; 24 passed)
- [x] 1.3 Once troupe#505 has merged, rebase onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports
      nothing about troupe's specs or Purposes. Keep the output for the pull request. Stop and revise the change if it
      reports anything of this change's. On 29d0347 (rebased onto ac4cd39, after troupe#505 merged as 4e5e2612): the
      Purpose read from troupe's `main` equals the record, and `oob: no differences (... troupe specs, troupe label
      descriptions, ...)`

## 2. Verify

- [x] 2.1 Run `openspec validate config-renames-purpose --strict` and verify it passes (passes)
- [x] 2.2 Verify no plan runs, since only `oob/` and `openspec/` change: `scripts/plan_needed.py` over the diff prints
      `plan=false` (it does)

## Workflow follow-up

- Open the draft pull request with `Closes #392` once group 1's first two tasks are done. Archive the change and
  rebase onto `main` in one push before marking it ready, after troupe#505 merges.
- The owner merges by rebase, through the merge queue, promptly after troupe#505.
- After the merge, check the next `drift (out of band)` run passes (or re-run that job).
- Check #392 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #392 with the pull request and the archived change.
