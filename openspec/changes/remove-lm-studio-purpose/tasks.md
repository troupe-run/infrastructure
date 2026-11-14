# Tasks

## 1. Remove the record

- [x] 1.1 Delete the `lm-studio-runner` line from `oob/troupe-spec-purposes.json` (design D1). Verify the file parses,
      has one entry fewer, its keys are still sorted, and `git diff` shows only that line removed (33 entries, sorted, one line removed)
- [x] 1.2 Leave `tofu/labels/troupe.json` unchanged (design D2). Verify `git diff tofu/` is empty and
      `scripts/tests/test_labels.py` passes (empty; 24 passed)

## 2. Verify against troupe's main

- [ ] 2.1 Once troupe's `remove-lm-studio` pull request has merged (design D3), check troupe's `main` has no
      `openspec/specs/lm-studio-runner/` (`gh api repos/troupe-run/troupe/contents/openspec/specs/lm-studio-runner`
      returns 404). Stop and revise the change if it's still there
- [ ] 2.2 Rebase the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports nothing about
      troupe's specs or Purposes. Keep the output for the pull request
- [ ] 2.3 Once the owner approves the pull request's `plan-pr` run, read its plan comment and verify it shows nothing
      created, changed or deleted, or that no plan ran because only `oob/` and `openspec/` changed
- [ ] 2.4 Run `openspec validate remove-lm-studio-purpose --strict` and verify it passes

## Workflow follow-up

- Open the draft pull request with `Closes #305` once group 1 is done. Mark it ready only after 2.1 and 2.2 have run
  against troupe's `main`, with `oob.py`'s output from 2.2. Archive the change and rebase onto `main` in one push
  before the last approval.
- The owner merges by rebase, through the merge queue, after troupe's `remove-lm-studio` pull request.
- After the merge, check the next `drift (out of band)` run passes (or re-run that job).
- Check #305 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #305 with the pull request and the archived change.
