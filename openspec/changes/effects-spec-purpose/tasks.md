# Tasks

## 1. Record the Purpose and reword the description

- [x] 1.1 Read the `effects` Purpose from troupe#273's branch
      (`gh api "repos/troupe-run/troupe/contents/openspec/changes/declared-effects/specs/effects/spec.md?ref=declared-effects"`,
      through `scripts/oob.py`'s `purpose()`), and add it to `oob/troupe-spec-purposes.json` where design D1 says.
      Verify the file has 30 entries, its keys are sorted, the entry matches #264's quote, and `git diff` shows only
      that added line (ca8431c: 30 entries, sorted, #264's quote, one line added)
- [x] 1.2 Set `cap:effects`'s description in `tofu/labels/troupe.json` to design D2's text. Verify the file still holds
      36 labels, `git diff` shows only that description, it is 100 characters, and `scripts/tests/test_labels.py`
      passes (36 labels, one description changed, 100 characters, 24 passed)

## 2. Verify against troupe's main

- [x] 2.1 Once troupe#273 has merged (design D3), re-read the Purpose from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/effects/spec.md`, through `purpose()`) and compare it with
      the record. Verify the spec's `Capability:` line still names `cap:effects` and `cap:config`. If the Purpose
      changed, update the record, check design D2 against the new text, and re-run 1.1–1.2's checks. Stop and revise
      the change if the spec is renamed, dropped or names other labels (troupe `main` 97c1a2d, troupe#273's merge:
      the Purpose matches the record, Capability line unchanged)
- [x] 2.2 Fast-forward the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports nothing about
      troupe's specs or Purposes, and exactly one difference of this change's: the board's `effects` option still has
      the old description (design D3). Keep the output for the pull request. Stop and revise the change if it reports
      anything else (10c5543, 0 behind `origin/main` e2811fa: exactly the board's `effects` option,
      "oob: 1 difference(s)")
- [ ] 2.3 Once the owner approves the pull request's first `plan-pr` run, read its plan comment and verify it shows only
      `cap:effects`'s description updated in place on troupe-run/troupe, and nothing else created, changed or deleted.
      Tick this in the same push as the archive, so the owner approves one more run
- [ ] 2.4 Run `openspec validate effects-spec-purpose --strict` and verify it passes

## Workflow follow-up

- Open the draft pull request with `Closes #264` once group 1 is done. Mark it ready only after 2.1 and 2.2 have run
  against troupe's `main` (design D3), with `oob.py`'s output from 2.2. Its plan comment is 2.3's evidence. Before the
  second `plan-pr` approval, archive the change and rebase onto `main`'s state commit in one push.
- The owner merges by rebase, through the merge queue, after troupe#273.
- After the merge, the owner reads the `plan (main)` plan, which also lists the `effects` option's description to set,
  and approves the `apply` job. Verify the description with `gh label list -R troupe-run/troupe --search cap:effects`,
  check `board descriptions (main)` succeeded, then check the next `drift (out of band)` run passes (or re-run that
  job), since the merge's own run checks before the board is set.
- Check #264 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #264 with the pull request and the archived change.
