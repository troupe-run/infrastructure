# Tasks

## 1. Add the labels and record the Purposes

- [x] 1.1 Read the `run-workspaces` and `claude-code-runner` Purposes from troupe's `main` through `scripts/oob.py`'s
      `purpose()` (design D2), and add them to `oob/troupe-spec-purposes.json` where D2 says. Verify the file has 25
      entries and its keys are in byte order (`jq -r 'keys_unsorted[]'` against `LC_ALL=C sort`)
- [x] 1.2 Add `cap:run-workspaces` and `cap:claude-code-runner` to `tofu/labels/troupe.json`, colour `1D76DB`, with
      design D1's descriptions, where D2 says. Verify the file holds 48 labels in byte order (`jq -r '.[].name'`
      against `LC_ALL=C sort`), that `git diff` shows only the two additions, and that `uv run scripts/check.py`
      passes

## 2. Verify

- [x] 2.1 Fast-forward the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports nothing for
      troupe's specs or label descriptions; keep its output for the pull request. If it reports a changed Purpose for
      either spec, update the record and the description together (design D2) and re-run 1.2's checks. Stop and
      revise the change if it reports anything else about troupe's labels
- [x] 2.2 Run `openspec validate cap-labels-for-new-specs --strict` and verify it passes
- [ ] 2.3 Once the owner approves the pull request's first `plan-pr` run, read its plan comment and verify it shows
      the two labels created on troupe-run/troupe, and nothing else created, changed or deleted. Tick this in the same
      push as the archive, so the owner approves one more run

## Workflow follow-up

- Open the pull request with `Closes #132`, `oob.py`'s output from 2.1 and design D3's table. Its plan comment is
  2.3's evidence. Before the second `plan-pr` approval, archive the change and rebase onto `main`'s state commit in
  one push.
- The owner merges by rebase.
- After the merge, the owner reads the `plan (main)` plan and approves the `apply` job. Verify the labels with
  `gh label list -R troupe-run/troupe`, and check that the next `drift (out of band)` run reports no `troupe specs`
  difference.
- Add the labels to the issues in design D3: read each one's labels first, add only its new label with
  `gh issue edit`, then verify with `gh issue view <n> -R troupe-run/troupe --json labels`.
- Check #132 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #132 with the pull request, the archived change and the labelled issues.
