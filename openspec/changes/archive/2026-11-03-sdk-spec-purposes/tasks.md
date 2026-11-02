# Tasks

## 1. Record the Purposes and widen the descriptions

- [x] 1.1 Read the `plugin-sdk` and `runner-tools` Purposes from troupe#268's branch
      (`gh api "repos/troupe-run/troupe/contents/openspec/changes/runner-sdk/specs/<name>/spec.md?ref=runner-sdk"`,
      through `scripts/oob.py`'s `purpose()`), and add them to `oob/troupe-spec-purposes.json` where design D1 says.
      Verify the file has 29 entries, its keys are sorted (`jq -r 'keys_unsorted[]'` against `sort`), each new entry
      matches #262's quote, and `git diff` shows only those two added lines
- [x] 1.2 Set `cap:plugins`'s and `cap:actor-runners`'s descriptions in `tofu/labels/troupe.json` to design D2's text.
      Verify the file still holds 36 labels, `git diff` shows only those two descriptions, they are 85 and 98
      characters, and `uv run scripts/check.py` passes

## 2. Verify against troupe's main

- [x] 2.1 Once troupe#268 has merged (design D3), re-read both Purposes from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md`, through `purpose()`) and compare them
      with the record. Verify each spec's `Capability:` line still names the labels in design's Context. If a Purpose
      changed, update the record, check design D2 against the new text, and re-run 1.1–1.2's checks. Stop and revise
      the change if a spec is renamed, dropped or names other labels (troupe `main` e4a33c2, troupe#268's merge: both
      Purposes match the record, Capability lines unchanged)
- [x] 2.2 Fast-forward the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports nothing about
      troupe's specs or Purposes, and exactly two differences of this change's: the board's `plugins` and
      `actor-runners` options still have the old descriptions (design D4). If #261 hasn't merged, its App
      `pull_requests: read` difference shows too; name it as #261's. Keep the output for the pull request. Stop and
      revise the change if it reports anything else (c6d710c, 0 behind `origin/main` c8f7466, #261 merged: exactly the
      two board options, "oob: 2 difference(s)")
- [x] 2.3 Once the owner approves the pull request's first `plan-pr` run, read its plan comment and verify it shows
      only `cap:plugins`' and `cap:actor-runners`' descriptions updated in place on troupe-run/troupe, and nothing
      else created, changed or deleted. Tick this in the same push as the archive, so the owner approves one more run (plan for 83e571f, run
      41457719962: 0 to add, 1 to change, 0 to destroy, the two labels' descriptions only)
- [x] 2.4 Run `openspec validate sdk-spec-purposes --strict` and verify it passes

## Workflow follow-up

- Open the draft pull request with `Closes #262` once group 1 is done. Mark it ready only after 2.1 and 2.2 have run
  against troupe's `main` (design D3), with `oob.py`'s output from 2.2. Its plan comment is 2.3's evidence. Before the
  second `plan-pr` approval, archive the change and rebase onto `main`'s state commit in one push.
- The owner merges by rebase, through the merge queue, after troupe#268.
- After the merge, the owner reads the `plan (main)` plan, which also lists the `plugins` and `actor-runners` options'
  descriptions to set, and approves the `apply` job. Verify the descriptions with
  `gh label list -R troupe-run/troupe --search cap:`, check `board descriptions (main)` succeeded, then check the next
  `drift (out of band)` run passes (or re-run that job), since the merge's own run checks before the board is set
  (design D4).
- Check #262 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #262 with the pull request and the archived change.
