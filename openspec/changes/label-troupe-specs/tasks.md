# Tasks

## 1. Add the three capability labels

- [ ] 1.1 Run `uv run scripts/oob.py` and verify that troupe's labels have exactly the four differences in design
      Context and nothing else; if there's more, stop and report it on #63
- [ ] 1.2 Read the flake-hunt, python-support and quality-check Purposes from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md`), collapse their whitespace the way
      `scripts/oob.py`'s `purpose()` does, and add them to `oob/troupe-spec-purposes.json` in name order (design D2)
- [ ] 1.3 Add `cap:flake-hunt`, `cap:python-support` and `cap:quality-check` to `tofu/labels/troupe.json`, colour
      `1D76DB`, with the descriptions in design D1, in name order. Verify the file holds 43 labels, sorted by name
      (`jq -r '.[].name'` against `sort`), that `git diff` shows only the three additions, and that
      `uv run scripts/check.py` passes

## 2. Record cap:releases's Purpose

- [ ] 2.1 Read the releases Purpose from troupe's `main` as in 1.2, check `cap:releases`'s description against it
      (design D3), and add it to `oob/troupe-spec-purposes.json` after `cap:quality-check`. Verify the file has 19
      entries and its keys are sorted (`jq -r 'keys_unsorted[]'` against `sort`)

## 3. Add the speed label

- [ ] 3.1 In `scripts/tests/test_labels.py`, write a test that a kind label in `tofu/labels/kinds.json` over 100
      characters is named with its length, and one that every declared kind label is within the limit. Run them and
      verify they fail because `kinds.json` doesn't exist yet
- [ ] 3.2 Create `tofu/labels/kinds.json` holding `speed` as in design D4, and verify 3.1's tests pass
- [ ] 3.3 Add the kind labels to all four repositories' label sets in `tofu/repositories.tf`, after the workflow's
      labels, with a comment saying what the set is for (design D4). Verify `tofu fmt` and `tofu validate` are clean
      and `uv run scripts/check.py` passes

## 4. Verify

- [ ] 4.1 Run `uv run scripts/oob.py` on the branch and verify it reports nothing for troupe's specs or labels; keep
      its output for the pull request
- [ ] 4.2 Run `uv run scripts/tofu.py plan` and verify it shows the three `cap:` labels created on troupe-run/troupe,
      `speed` created on troupe, `.github`, infrastructure and website, and nothing else created, changed or deleted;
      keep its output for the pull request
- [ ] 4.3 Run `openspec validate label-troupe-specs --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #63`, the plan from 4.2, `oob.py`'s output from 4.1 and design D5's relabelling
  table. The owner approves the `plan-pr` run.
- Archive the change on the branch before merging; the owner merges by rebase.
- After the merge, the owner reads the `plan (main)` plan and approves the `apply` job. Verify the labels with
  `gh label list -R troupe-run/<repo>` for each repository (a read), and run `uv run scripts/oob.py` on `main` to
  verify it reports nothing for troupe's labels.
- Relabel the issues in design D5: read each one's labels first, make only D5's adds and removes with
  `gh issue edit`, then verify with `gh issue view <n> --json labels`. Verify `cap:performance` is left only on
  troupe#36 (`gh issue list -R troupe-run/troupe --state all --label cap:performance`).
- Check #63 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #63 with the pull request, the archived change and the relabelled issues.
