# Tasks

## 1. Declare the labels

- [ ] 1.1 Re-read troupe's spec folders on `main` (`gh api repos/troupe-run/troupe/contents/openspec/specs`) and
      verify `client-protocol` and `runs` are still the only ones without a declared `cap:` label
- [ ] 1.2 Add `cap:client-protocol` (after `cap:cli`) and `cap:runs` (after `cap:runner-protocol`) to
      `tofu/labels/troupe.json`, colour `1D76DB`, description `Capability: <name>` (design D1), and verify the file
      holds 39 labels, is still sorted by name (`jq -r '.[].name'` against `sort`), and `uv run scripts/check.py`
      passes
- [ ] 1.3 Run `uv run scripts/tofu.py plan` and verify it shows exactly two labels created on troupe-run/troupe and
      nothing else changed or deleted; keep its output for the pull request
- [ ] 1.4 Run `uv run scripts/oob.py` on this branch and verify it reports nothing for troupe's specs; keep its output
      for the pull request
- [ ] 1.5 Run `openspec validate runs-and-client-protocol-labels --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #25`, the plan from 1.3 and `oob.py`'s output from 1.4. The owner approves the
  `plan-pr` run.
- Archive the change on the branch before merging; the owner merges by rebase.
- After the merge, the owner reads the `plan (main)` plan and approves the `apply` job. Verify the two labels exist
  with `gh label list -R troupe-run/troupe --search cap:` (a read).
- Label troupe's issues (design D2): `cap:runs` on #3, #4, #33, #36, #51 and #54, `cap:client-protocol` on #14, #33
  and #36, with `gh issue edit <n> -R troupe-run/troupe --add-label …`. Verify with
  `gh issue list -R troupe-run/troupe --state all --label cap:runs` and `--label cap:client-protocol` that exactly
  those issues carry them.
- Run `uv run scripts/oob.py` on `main` and verify it reports no unlabelled troupe spec.
- Comment on #25 with the pull request, the archived change and the issues labelled, and close it.
