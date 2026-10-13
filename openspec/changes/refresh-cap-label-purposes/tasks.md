# Tasks

## 1. Refresh the two labels

- [x] 1.1 Run `uv run scripts/oob.py` and verify that troupe's labels have exactly the two differences in design
      Context (`cap:platform` Purpose changed, `cap:protocol` not recorded) and nothing else; if there's more, stop
      and report it on #29
- [x] 1.2 Read the platform and protocol Purposes from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md`), collapse their whitespace the way
      `scripts/oob.py`'s `purpose()` does, and write them to `oob/troupe-spec-purposes.json`: replace `cap:platform`'s
      entry and add `cap:protocol` after `cap:policy` (design D3). Verify the file has 15 entries and its keys are
      sorted (`jq -r 'keys_unsorted[]'` against `sort`)
- [x] 1.3 Change `cap:platform`'s and `cap:protocol`'s descriptions in `tofu/labels/troupe.json` to the text in design
      D1 and D2, and verify the file still holds 39 labels, sorted by name, with only those two descriptions changed
      (`git diff`), and that `uv run scripts/check.py` passes
- [x] 1.4 Run `uv run scripts/oob.py` on the branch and verify it reports nothing for troupe's labels; keep its output
      for the pull request
- [x] 1.5 Run `uv run scripts/tofu.py plan` and verify it shows exactly two in-place label description updates on
      troupe-run/troupe and nothing created, deleted or otherwise changed; keep its output for the pull request
- [x] 1.6 Run `openspec validate refresh-cap-label-purposes --strict` and verify it passes

## Workflow follow-up

- Settle design's Open Question with the owner before opening the pull request. With (a), open the `cap:releases`
  issue first (its trigger: troupe-run/troupe#23's change archives; its contents: #29's `cap:releases` item) and put
  `Closes #29` in the pull request. With (b), open the narrow issue and close that instead.
- Open the pull request with the plan from 1.5 and `oob.py`'s output from 1.4. The owner approves the `plan-pr` run.
- Archive the change on the branch before merging; the owner merges by rebase.
- After the merge, the owner reads the `plan (main)` plan and approves the `apply` job. Verify both descriptions with
  `gh label list -R troupe-run/troupe --search cap:p` (a read).
- Run `uv run scripts/oob.py` on `main` and verify it reports nothing for troupe's labels.
- Comment on #29 with the pull request and the archived change, and tick `cap:platform`. Add `cap:protocol` as a
  done item, since #29 didn't list it.
