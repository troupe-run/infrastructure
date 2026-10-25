# Tasks

## 1. The check

- [ ] 1.1 Before changing the check, verify `uv run pytest scripts/tests/test_milestones.py` passes on the branch as it
  is, so every existing rule is known to hold before the new one is added.
- [ ] 1.2 In `scripts/tests/test_milestones.py`, add tests for the new rule (design D2), each named for what it asserts:
  a straight apostrophe is named with ’ and ‘; a straight double quote is named with “ and ”; a description with both
  gets one message for each; a description with ’, ‘, “ and ” is valid. Verify they fail before 1.3, for the right
  reason.
- [ ] 1.3 Add the description rule to `declaration_problems`, with a comment naming this change's design D2, and
  update its docstring. Verify the tests from 1.2 and every existing test pass, and that
  `test_the_declared_milestones_are_well_formed` now fails, naming the four milestones (0.2.0, 0.3.0, 0.6.0, 0.14.0)
  and nothing else.

## 2. The descriptions

- [ ] 2.1 In `tofu/milestones.json`, replace the straight apostrophe in each of the four descriptions (keys `0.14.0`,
  `0.2.0`, `0.5.0`, `0.13.0`) with the raw character ’ (design D1). Verify `git diff` changes only those four lines,
  one character each, and that the file has no `’` escape.
- [ ] 2.2 Verify `uv run scripts/check.py` passes, including `test_the_declared_milestones_are_well_formed`.
- [ ] 2.3 Fast-forward onto `origin/main` and run a local plan. Verify it shows 16 updates in place, four in each of
  troupe, infrastructure, website and `.github`, each changing only `description`, and nothing created, destroyed or
  replaced.
- [ ] 2.4 Open the pull request with `Closes #127`, using `--body-file`. Verify the CI plan comment shows the same
  counts as 2.3 and prints ’ in the description diffs.

## Workflow follow-up

- Archive the change on the branch in the same push as ticking 2.4, and rebase onto `main`'s latest state commit
  before asking for the plan approval (memory: archive before plan approval).
- After the owner merges, check the milestones notice (design D3): a `milestones-notice` run on the merge commit
  succeeded, and a website Deploy run on `main`, triggered by `workflow_dispatch`, started after it and succeeded. Then
  check troupe.run/status/ shows the four descriptions with ’.
- After the owner approves the apply, verify on GitHub that in each of the four repositories the four milestones'
  descriptions have ’ and no milestone description has `'` or `"`
  (`gh api repos/troupe-run/<repo>/milestones?state=all`).
- Check #127 is closed with a comment naming the PR and the archived change, and its card says Done. Mention that the
  fourth description (0.2.0, "Other runners") was fixed too, and that the optional check was included.
