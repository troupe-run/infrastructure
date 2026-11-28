# Tasks

## 1. Record the Purpose

- [x] 1.1 Read the `performances` Purpose through `scripts/oob.py`'s `purpose()` from troupe's `main`, and add it to
      `oob/troupe-spec-purposes.json` where design D1 says. Verify the keys are sorted, the entry matches #425's quote,
      and `git diff` shows only that added line (39 entries, sorted, #425's quote, one line added between
      `openai-runner` and `platform`; read from troupe's `main` at 4e77cc28)
- [x] 1.2 Check the descriptions of `cap:runs` and `cap:lineage` against the Purpose (design D2), and leave
      `tofu/labels/troupe.json` unchanged. Verify `git diff tofu/labels/` is empty and `scripts/tests/test_labels.py`
      passes (empty; 24 passed)
- [x] 1.3 Run `uv run scripts/oob.py`. Verify it reports nothing about troupe's specs or Purposes, and keep the output
      for the pull request. Stop and revise the change if it reports anything of this change's (`oob: no differences
      (... troupe specs, troupe label descriptions, ...)`)

## 2. Verify

- [x] 2.1 Run `openspec validate record-performances-spec-purpose --strict` and verify it passes (valid)
- [x] 2.2 Run `uv run scripts/check.py` with its output kept in a scratch file, and verify every gate passes (all
      gates passed)

## Workflow follow-up

- Open the draft pull request with `Closes #425`. Archive the change before marking it ready.
- The owner merges by rebase, through the merge queue.
- After the merge, check the next `drift (out of band)` run passes (or re-run that job).
- Check #425 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #425 with the pull request and the archived change.
