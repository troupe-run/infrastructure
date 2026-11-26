# Tasks

## 1. Record the Purpose

- [ ] 1.1 Read the `gates` Purpose through `scripts/oob.py`'s `purpose()` from troupe's `main`, and add it to
      `oob/troupe-spec-purposes.json` where design D1 says. Verify the keys are sorted, the entry matches #419's quote,
      and `git diff` shows only that added line
- [ ] 1.2 Check the descriptions of `cap:gates` and `cap:cues` against the Purpose (design D2), and leave
      `tofu/labels/troupe.json` unchanged. Verify `git diff tofu/labels/` is empty and `scripts/tests/test_labels.py`
      passes
- [ ] 1.3 Run `uv run scripts/oob.py`. Verify it reports nothing about troupe's specs or Purposes, and keep the output
      for the pull request. Stop and revise the change if it reports anything of this change's

## 2. The 0.4.0 description

- [ ] 2.1 Change the `description` of the milestone titled `0.4.0` in `tofu/milestones.json` to design D3's text, and
      nothing else. Verify `git diff tofu/milestones.json` is that one line, and `scripts/tests/test_milestones.py`
      passes
- [ ] 2.2 Verify a plan is needed, since `tofu/` changes: `scripts/plan_needed.py` over the diff prints `plan=true`
- [ ] 2.3 Once CI's plan of the pull request is posted, read it. Verify it updates only the `description` of the 0.4.0
      milestone in each repository in `repositories`, and nothing else. Stop and revise the change if it shows more

## 3. Verify

- [ ] 3.1 Run `openspec validate record-gates-spec-purpose --strict` and verify it passes
- [ ] 3.2 Run `uv run scripts/check.py` with its output kept in a scratch file, and verify every gate passes

## Workflow follow-up

- Open the draft pull request with `Closes #419`. Archive the change before marking it ready.
- The owner merges by rebase, through the merge queue, and approves the `apply` job of `main`'s run.
- After the merge and apply, check the next `drift (out of band)` run passes (or re-run that job), and that the 0.4.0
  milestone shows the new description on GitHub.
- Check #419 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #419 with the pull request and the archived change.
