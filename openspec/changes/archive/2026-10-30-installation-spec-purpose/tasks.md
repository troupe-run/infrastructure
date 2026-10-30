# Tasks

## 1. Record the Purpose and widen the description

- [x] 1.1 Read the `installation` Purpose from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/installation/spec.md`, through `scripts/oob.py`'s
      `purpose()`), and add it to `oob/troupe-spec-purposes.json` where design D1 says. Verify the file has 26
      entries, its keys are sorted (`jq -r 'keys_unsorted[]'` against `sort`), and the new entry matches #224's quote
- [x] 1.2 Set `cap:development`'s description in `tofu/labels/troupe.json` to design D2's text. Verify the file
      still holds 36 labels, `git diff` shows only that one description, it is 99 characters, and
      `uv run scripts/check.py` passes

## 2. Verify

- [x] 2.1 Fast-forward the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports exactly one
      difference: the board's `development` option still has `cap:development`'s old description (design D4). Keep
      its output for the pull request. If it reports a changed `installation` Purpose, update the record and design
      D2 together and re-run 1.1 and 1.2's checks. Stop and revise the change if it reports anything else
- [x] 2.2 Once the owner approves the pull request's first `plan-pr` run, read its plan comment and verify it shows
      only `cap:development`'s description updated in place on troupe-run/troupe, and nothing else created, changed
      or deleted. The board's `development` option isn't in it: only `plan (main)` plans board descriptions (design
      D4). Tick this in the same push as the archive, so the owner approves one more run. (Plan for 2021507, run
      40975339151: 0 to add, 1 to change, 0 to destroy, the one label.)
- [x] 2.3 Run `openspec validate installation-spec-purpose --strict` and verify it passes

## 3. The note in troupe

- [x] 3.1 Raise a troupe-run/troupe issue, with `--project "troupe roadmap"`, asking for a line in troupe's
      `openspec/config.yaml`, beside the #152 label rule: every new spec's Purpose is recorded in
      troupe-run/infrastructure's `oob/troupe-spec-purposes.json`, in a pull request that lands with or before the
      spec. Say it arose from #224 (design D3). Verify it's on the board with
      `gh issue view <n> -R troupe-run/troupe --json projectItems` (troupe#199, on the board at Todo)

## Workflow follow-up

- Open the pull request with `Closes #224`, `oob.py`'s output from 2.1 and the troupe issue from 3.1. Its plan
  comment is 2.2's evidence. Before the second `plan-pr` approval, archive the change and rebase onto `main`'s state
  commit in one push.
- The owner merges by rebase, through the merge queue.
- After the merge, the owner reads the `plan (main)` plan, which also lists the `development` option's description
  to set, and approves the `apply` job. Verify the description with
  `gh label list -R troupe-run/troupe --search cap:development`, check `board descriptions (main)` succeeded, then
  check the next `drift (out of band)` run passes (or re-run that job), since the merge's own run checks before the
  board is set (design D4).
- Check #224 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #224 with the pull request, the archived change and the troupe issue.
