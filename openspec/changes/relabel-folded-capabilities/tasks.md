# Tasks

## 1. Inventory (design D1, D3 step 1)

- [x] 1.1 Fast-forward onto `origin/main` if only a state commit is ahead. Read troupe's `main` specs with
  `oob.py`'s `spec_documents` and `capability_labels`, and print the labels each of the 12 folded labels' specs
  names. Verify it matches design's first table, and record any difference here (the read wins). Result: `main` was current. All 12 match the table, with no difference
- [x] 1.2 List every troupe-run/troupe issue and pull request, open and closed, with its labels (`gh issue list
  --state all` and `gh pr list --state all`, with a limit above the repository's count). Compute, per D2, the
  removals (each folded label an issue or PR carries) and the additions (the union of its specs' labels, less what it
  already carries). Write `relabel.md` in this change: each affected issue with its labels before, its additions and
  its removals, and the exact add and remove commands grouped by label. Verify the totals (59 removals, 43 additions
  on 36 issues, no pull requests, `cap:lifecycle` on nothing, as of 2026-10-26), and that every label to add is
  declared in `tofu/labels/troupe.json` and exists on troupe-run/troupe (`gh label list`). Record any difference from
  design's tables here and in `relabel.md`. Commit `relabel.md` before any edit. Result: read 120 issues and 47 pull requests. 43 issues
  (14 open), no pull request; 59 removals, 43 additions on 36 issues; `cap:lifecycle` on nothing. All 10 labels to add
  are declared and on GitHub. No difference from design

## 2. Relabel troupe's issues (design D2, D3 steps 2-5)

- [ ] 2.1 Run the add commands from `relabel.md`, one `gh issue edit <n>... -R troupe-run/troupe --add-label
  <label>` per label, in the shell. Verify against GitHub, re-reading every issue that carries a folded label, that
  each carries every label its folded labels' specs name. Stop and record here if any doesn't.
- [ ] 2.2 Run the remove commands from `relabel.md`, one `gh issue edit <n>... -R troupe-run/troupe --remove-label
  <folded>` per folded label. Verify that `gh issue list` and `gh pr list` with `--state all --label <l>` return
  nothing for each of the 13 labels, and that each edited issue's labels now equal its "before" labels minus its
  folded labels plus its additions (a script comparing GitHub with `relabel.md`). Record the result in `relabel.md`
  and here, and commit it.

## 3. Remove the 13 labels from the declaration (design D4, D5)

- [ ] 3.1 Delete the 12 folded labels and `cap:lifecycle` from `tofu/labels/troupe.json`. Verify it has 36 labels,
  still in byte order, with `uv run pytest scripts/tests/test_labels.py`, and that `git grep` outside
  `openspec/changes/archive` and this change finds none of the 13 names except where the `labels` spec quotes them
  as examples.
- [ ] 3.2 Check that no oob record is keyed by, or names, a removed label (D5): `git grep -n "cap:" -- oob/` names
  none of the 13, and `oob/troupe-spec-purposes.json`'s keys are all specs on troupe's `main`. Remove any record
  found, and say so here. Then run `uv run scripts/oob.py` and verify it reports no `troupe specs` or `troupe labels`
  difference. Record its output here.
- [ ] 3.3 Run `uv run scripts/check.py` and verify every gate passes, including `openspec validate --strict` for
  this change.

## 4. Integration checks

- [ ] 4.1 Fast-forward onto `origin/main` if only a state commit is ahead, then run `uv run scripts/tofu.py plan`.
  Verify `Plan: 0 to add, 1 to change, 0 to destroy.`, with `module.repo_troupe.github_issue_labels.this` changing in
  place by removing exactly the 13 labels, and no label added or changed. Record the summary here. If 1Password's
  approval can't be given, the PR's CI plan stands in for it, as on #160.
- [ ] 4.2 Re-run 2.2's check for the 13 labels just before opening the pull request. Push and open it (`Closes
  #151`), its description listing for each of the 13 labels the troupe issues and pull requests that carry it, read
  then: none. Verify CI passes and the plan comment matches 4.1.

## Workflow follow-up

- Archive the change on the branch, rebase onto `main`'s state commit, and re-run 2.2's check before asking once for
  the plan's approval.
- After the merge and the apply: verify on GitHub that troupe-run/troupe has none of the 13 labels and 36 `cap:`
  labels, and that the `tofu` workflow's drift job reports nothing new.
- Comment on #151 with the PR and the archived change, check it's closed and its card says Done.
- Tell #152's session (worktree `infrastructure-capability-label-standard-change`) that the labels are final, so the
  owner can remove the board's `lifecycle` option and #152 can merge.
