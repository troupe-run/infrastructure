# Tasks

## 1. Record the Purpose

- [x] 1.1 Read the `lm-studio-runner` Purpose from troupe#379's branch
      (`gh api "repos/troupe-run/troupe/contents/openspec/changes/lmstudio-runner/specs/lm-studio-runner/spec.md?ref=lmstudio-runner"`,
      through `scripts/oob.py`'s `purpose()`), and add it to `oob/troupe-spec-purposes.json` where design D1 says.
      Verify the file has 34 entries, its keys are sorted, the entry matches #296's quote, and `git diff` shows only
      that added line (34 entries, sorted, #296's quote, one line added; between `lineage` and `ollama-runner`)
- [x] 1.2 Check `cap:actor-runners`' description against the Purpose (design D2), and leave `tofu/labels/troupe.json`
      unchanged. Verify `git diff tofu/` is empty and `scripts/tests/test_labels.py` passes (empty; 24 passed)

## 2. Verify against troupe's main

- [x] 2.1 Once troupe#379 has merged (design D3), re-read the Purpose from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/lm-studio-runner/spec.md`, through `purpose()`) and compare
      it with the record. Verify the spec's `Capability:` line still names `cap:actor-runners` alone. If the Purpose
      changed, update the record, check design D2 against the new text, and re-run 1.1's checks. Stop and revise the
      change if the spec is renamed, dropped or names other labels
      Done 2026-11-12, after troupe#379 merged (025928d4): `purpose()` of `main`'s spec equals the record, and its
      `Capability:` line is `cap:actor-runners` alone.
- [x] 2.2 Fast-forward the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports nothing about
      troupe's specs or Purposes. Keep the output for the pull request. Stop and revise the change if it reports
      anything of this change's
      Done 2026-11-12 on `origin/main`: "oob: no differences (... troupe specs, troupe label descriptions, ...)".
- [x] 2.3 Once the owner approves the pull request's `plan-pr` run, read its plan comment and verify it shows nothing
      of this change's created, changed or deleted (any change listed is another pending one of `main`'s, named in
      the tick), or that no plan ran because only `oob/` and `openspec/` changed
      Done: no plan ran. "does it need a plan?" passed and `plan (pull request)` was skipped, since only `oob/` and
      `openspec/` change.
- [x] 2.4 Run `openspec validate lm-studio-runner-spec-purpose --strict` and verify it passes
      Done 2026-11-12: it passes.

## Workflow follow-up

- Open the draft pull request with `Closes #296` once group 1 is done. Mark it ready only after 2.1 and 2.2 have run
  against troupe's `main` (design D3), with `oob.py`'s output from 2.2. Archive the change and rebase onto `main` in
  one push before the last approval.
- The owner merges by rebase, through the merge queue, after troupe#379.
- After the merge, check the next `drift (out of band)` run passes (or re-run that job).
- Check #296 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #296 with the pull request and the archived change.
