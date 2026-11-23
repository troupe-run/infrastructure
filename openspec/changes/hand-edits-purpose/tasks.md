# Tasks

## 1. Record the Purpose

- [x] 1.1 Read the `config-hand-edits` Purpose from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/config-hand-edits/spec.md`, through
      `scripts/oob.py`'s `purpose()`), and add it to `oob/troupe-spec-purposes.json` where design D1 says. Verify the
      file has 36 entries, its keys are sorted, the entry matches #382's quote, and `git diff` shows only that added
      line (36 entries, sorted, #382's quote, one line added; between `config-files` and `docs-publishing`)
- [x] 1.2 Check the descriptions of `cap:config`, `cap:projections` and `cap:lineage` against the Purpose (design
      D2), and leave `tofu/labels/troupe.json` unchanged. Verify `git diff tofu/` is empty and
      `scripts/tests/test_labels.py` passes (empty; 24 passed)
- [x] 1.3 Rebase onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports nothing about troupe's specs or
      Purposes. Keep the output for the pull request. Stop and revise the change if it reports anything of this
      change's. On 4d8fda3 (no rebase needed): `oob: no differences (... troupe specs, troupe label descriptions, ...)`

## 2. Verify

- [x] 2.1 Run `openspec validate hand-edits-purpose --strict` and verify it passes (passes)
- [ ] 2.2 Once the owner approves the pull request's `plan-pr` run (if one runs), read its plan comment and verify it
      shows nothing of this change's created, changed or deleted, or that no plan ran because only `oob/` and
      `openspec/` changed

## Workflow follow-up

- Open the draft pull request with `Closes #382` once group 1 is done. Archive the change and rebase onto `main` in
  one push before marking it ready.
- The owner merges by rebase, through the merge queue.
- After the merge, check the next `drift (out of band)` run passes (or re-run that job).
- Check #382 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #382 with the pull request and the archived change.
