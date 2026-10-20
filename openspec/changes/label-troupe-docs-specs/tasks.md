# Tasks

## 1. Add the two capability labels

- [x] 1.1 Read the user-docs and docs-publishing Purposes from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md`) through `scripts/oob.py`'s `purpose()`,
      and add them to `oob/troupe-spec-purposes.json` where design D2 says. Verify the file has 21 entries and its
      keys are sorted (`jq -r 'keys_unsorted[]'` against `sort`)
- [x] 1.2 Add `cap:docs-publishing` and `cap:user-docs` to `tofu/labels/troupe.json`, colour `1D76DB`, with the
      descriptions in design D1, where design D2 says. Verify the file holds 45 labels sorted by name
      (`jq -r '.[].name'` against `sort`), that `git diff` shows only the two additions, and that
      `uv run scripts/check.py` passes

## 2. Verify

- [x] 2.1 Run `uv run scripts/oob.py` on the branch and verify it reports nothing; keep its output for the pull request
- [x] 2.2 Run `uv run scripts/tofu.py plan` and verify it shows the two `cap:` labels created on troupe-run/troupe and
      nothing else created, changed or deleted; keep its output for the pull request
- [x] 2.3 Run `openspec validate label-troupe-docs-specs --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #112`, the plan from 2.2, `oob.py`'s output from 2.1 and design D3's relabelling
  table. The owner approves the `plan-pr` run once, after the archive is pushed (archive before plan approval).
- Archive the change on the branch before merging; the owner merges by rebase.
- After the merge, the owner reads the `plan (main)` plan and approves the `apply` job. Verify the labels with
  `gh label list -R troupe-run/troupe`, and check that the next drift job passes.
- Relabel the issues in design D3: read each one's labels first, make only D3's adds and removes with
  `gh issue edit`, then verify with `gh issue view <n> -R troupe-run/troupe --json labels`.
- Check #112 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #112 with the pull request, the archived change and the relabelled issues.
