# Tasks

## 1. Record the Purpose

- [x] 1.1 Read the `mistralrs-runner` Purpose from troupe's `in-process-runner` branch
      (`gh api "repos/troupe-run/troupe/contents/openspec/changes/in-process-runner/specs/mistralrs-runner/spec.md?ref=in-process-runner"`,
      through `scripts/oob.py`'s `purpose()`), and add it to `oob/troupe-spec-purposes.json` where design D1 says.
      Verify the file has 35 entries, its keys are sorted, the entry matches #307's quote, and `git diff` shows only
      that added line (35 entries, sorted, #307's quote, one line added; between `lm-studio-runner` and
      `ollama-runner`)
- [x] 1.2 Check `cap:actor-runners`' description against the Purpose (design D2), and leave `tofu/labels/troupe.json`
      unchanged. Verify `git diff tofu/` is empty and `scripts/tests/test_labels.py` passes (empty; 24 passed)

## 2. Verify against troupe's main

- [ ] 2.1 Once troupe's `in-process-runner` pull request has merged (design D3), re-read the Purpose from troupe's
      `main` (`gh api repos/troupe-run/troupe/contents/openspec/specs/mistralrs-runner/spec.md`, through `purpose()`)
      and compare it with the record. Verify the spec's `Capability:` line still names `cap:actor-runners` alone. If the
      Purpose changed, update the record, check design D2 against the new text, and re-run 1.1's checks. Stop and
      revise the change if the spec is renamed, dropped or names other labels
- [ ] 2.2 Rebase the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports nothing about
      troupe's specs or Purposes. Keep the output for the pull request. Stop and revise the change if it reports
      anything of this change's
- [ ] 2.3 Once the owner approves the pull request's `plan-pr` run, read its plan comment and verify it shows nothing
      of this change's created, changed or deleted, or that no plan ran because only `oob/` and `openspec/` changed
- [ ] 2.4 Run `openspec validate mistralrs-runner-spec-purpose --strict` and verify it passes

## Workflow follow-up

- Open the draft pull request with `Closes #307` once group 1 is done. Mark it ready only after 2.1 and 2.2 have run
  against troupe's `main` (design D3), with `oob.py`'s output from 2.2. Archive the change and rebase onto `main` in
  one push before the last approval.
- The owner merges by rebase, through the merge queue, after troupe's `in-process-runner` pull request.
- After the merge, check the next `drift (out of band)` run passes (or re-run that job).
- Check #307 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #307 with the pull request and the archived change.
