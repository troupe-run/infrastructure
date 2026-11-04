# Tasks

## 1. Record the Purpose

- [x] 1.1 Read the `ollama-runner` Purpose from troupe#283's branch
      (`gh api "repos/troupe-run/troupe/contents/openspec/changes/local-model-runner/specs/ollama-runner/spec.md?ref=local-model-runner"`,
      through `scripts/oob.py`'s `purpose()`), and add it to `oob/troupe-spec-purposes.json` where design D1 says.
      Verify the file has 31 entries, its keys are sorted, the entry matches #266's quote, and `git diff` shows only
      that added line (31 entries, sorted, #266's quote, one line added)
- [x] 1.2 Check `cap:actor-runners`' description against the Purpose (design D2), and leave `tofu/labels/troupe.json`
      unchanged. Verify `git diff tofu/` is empty and `scripts/tests/test_labels.py` passes (empty; 24 passed)

## 2. Verify against troupe's main

- [ ] 2.1 Once troupe#283 has merged (design D3), re-read the Purpose from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/ollama-runner/spec.md`, through `purpose()`) and compare
      it with the record. Verify the spec's `Capability:` line still names `cap:actor-runners` alone. If the Purpose
      changed, update the record, check design D2 against the new text, and re-run 1.1's checks. Stop and revise the
      change if the spec is renamed, dropped or names other labels
- [ ] 2.2 Fast-forward the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports nothing about
      troupe's specs or Purposes. Keep the output for the pull request. Stop and revise the change if it reports
      anything of this change's
- [ ] 2.3 Once the owner approves the pull request's `plan-pr` run, read its plan comment and verify it shows nothing
      of this change's created, changed or deleted (any change listed is another pending one of `main`'s, named in
      the tick)
- [ ] 2.4 Run `openspec validate ollama-runner-spec-purpose --strict` and verify it passes

## Workflow follow-up

- Open the draft pull request with `Closes #266` once group 1 is done. Mark it ready only after 2.1 and 2.2 have run
  against troupe's `main` (design D3), with `oob.py`'s output from 2.2. Archive the change and rebase onto `main` in
  one push before the last approval.
- The owner merges by rebase, through the merge queue, after troupe#283.
- After the merge, check the next `drift (out of band)` run passes (or re-run that job).
- Check #266 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #266 with the pull request and the archived change.
