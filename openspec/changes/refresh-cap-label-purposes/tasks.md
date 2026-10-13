# Tasks

## 1. Refresh cap:platform and cap:protocol

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

## 2. Add cap:releases

- [x] 2.1 Check troupe's `main` still has no `openspec/specs/releases/`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs --jq '.[].name'`); if it has one, record its Purpose
      as in 1.2 and review the description against it (design D4, Risks)
- [x] 2.2 Add `cap:releases` after `cap:protocol` in `tofu/labels/troupe.json`, colour `1D76DB`, with the
      description in design D4, and verify the file holds 40 labels, sorted by name (`jq -r '.[].name'` against
      `sort`), and that `uv run scripts/check.py` passes
- [x] 2.3 Run `uv run scripts/oob.py` and verify it reports nothing for troupe's labels; keep its output for the pull
      request in place of 1.4's
- [x] 2.4 Run `uv run scripts/tofu.py plan` and verify it shows `cap:releases` created and `cap:platform`'s and
      `cap:protocol`'s descriptions changed on troupe-run/troupe, with no other label or resource changed or deleted;
      keep its output for the pull request in place of 1.5's
- [x] 2.5 Run `openspec validate refresh-cap-label-purposes --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #29`, the plan from 2.4 and `oob.py`'s output from 2.3. The owner approves the
  `plan-pr` run.
- Archive the change on the branch before merging; the owner merges by rebase.
- After the merge, the owner reads the `plan (main)` plan and approves the `apply` job. Verify the two descriptions
  and the new label with `gh label list -R troupe-run/troupe --search cap:` (a read).
- Label troupe#23 (design D4) with `gh issue edit 23 -R troupe-run/troupe --add-label cap:releases`, and verify with
  `gh issue list -R troupe-run/troupe --state all --label cap:releases` that #23 is the only issue carrying it and
  still carries `cap:infrastructure`.
- Run `uv run scripts/oob.py` on `main` and verify it reports nothing for troupe's labels.
- Comment on #29 with the pull request and the archived change, tick `cap:platform` and `cap:releases`, and add
  `cap:protocol` as a done item, since #29 didn't list it. Say that `cap:releases`'s Purpose is recorded when
  `oob.py` reports it, after troupe#23's change archives.
