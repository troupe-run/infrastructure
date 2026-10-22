# Tasks

## 1. Add the label and record the Purposes

- [x] 1.1 Read the `config` and `config-files` Purposes from troupe's `config-model` branch
      (`openspec/changes/config-model/specs/<name>/spec.md`, through `scripts/oob.py`'s `purpose()`), and add them to
      `oob/troupe-spec-purposes.json` where design D2 says. Verify the file has 23 entries and its keys are sorted
      (`jq -r 'keys_unsorted[]'` against `sort`)
- [x] 1.2 Add `cap:config-files` to `tofu/labels/troupe.json`, colour `1D76DB`, and set `cap:config`'s description,
      both as design D1 says, with `cap:config-files` where D2 says. Verify the file holds 46 labels sorted by name
      (`jq -r '.[].name'` against `sort`), that `git diff` shows only the one addition and the one description, and
      that `uv run scripts/check.py` passes

## 2. Verify on the branch, before troupe#60 merges

- [x] 2.1 Run `uv run scripts/oob.py` on the branch and verify it reports exactly two differences: the recorded
      `cap:config` and `cap:config-files` Purposes have no spec on troupe's `main` (design D4)
- [x] 2.2 Verify the plan shows `cap:config-files` created and `cap:config`'s description updated on
      troupe-run/troupe, and nothing else created, changed or deleted. Read it from the pull request's `plan-pr` run,
      not a local `uv run scripts/tofu.py plan`: 1Password couldn't be reached on 2026-10-21 (owner away), and the
      owner chose the pull request's plan. So this is checked together with 3.2
- [x] 2.3 Run `openspec validate label-troupe-config-specs --strict` and verify it passes

## 3. Verify after troupe#60 merges

- [x] 3.1 Once troupe#60's change is on troupe's `main`, fast-forward this branch onto `origin/main` and run
      `uv run scripts/oob.py`. Verify it reports nothing; keep its output for the pull request. If it reports a
      changed Purpose for `config` or `config-files`, update the record and the description together (design D2)
      and re-run 1.2's checks. Stop and revise the change if it reports anything else
- [x] 3.2 Once the owner approves the pull request's first `plan-pr` run, read its plan comment and verify it shows
      only 2.2's two changes. Tick 2.2 and 3.2 in the same push as the archive, so the owner approves one more run

## Workflow follow-up

- Open the pull request with `Closes #116`, `oob.py`'s output from 3.1 and design D3's table.
  Its plan comment is 2.2 and 3.2's evidence. Before the second `plan-pr` approval, archive the change and rebase
  onto `main`'s state commit in one push.
- The owner merges by rebase, after troupe#60 (design D4).
- After the merge, the owner reads the `plan (main)` plan and approves the `apply` job. Verify the labels with
  `gh label list -R troupe-run/troupe`, and check that the next drift job passes.
- Add `cap:config-files` to the issues in design D3: read each one's labels first, add only that label with
  `gh issue edit`, then verify with `gh issue view <n> -R troupe-run/troupe --json labels`.
- Check #116 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #116 with the pull request, the archived change and the labelled issues.
