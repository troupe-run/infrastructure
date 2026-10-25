# Tasks

## 1. The rules, tested on this side

- [x] 1.1 Before changing the check, verify `uv run pytest scripts/tests/test_milestones.py` passes on the branch as it
  is, so every existing rule is known to hold before the new ones are added.
- [x] 1.2 In `scripts/tests/test_milestones.py`, add tests for the new rules (spec: milestones, "The milestone
  declaration is well formed"; design D1, D3), each named for what its body asserts:
  - shape: a top-level array, an object with no `milestones`, and a `milestones` that isn't an array each give the one
    shape problem;
  - an entry that isn't an object (a string, `null`, an array) is named by position and no other rule reports on it;
  - titles `v0.3.0`, `0.3`, `0.03.0`, `0.3.0.0`, `0.3.0 `, ` 0.3.0`, `0.3.0\n`, `٣.0.0` and `""` are each named by
    position with the title quoted and the fix; a title that's a number, `null` or missing is named by position;
  - titles `0.0.0`, `0.3.0` and `10.20.30` are valid;
  - descriptions that are `""`, `"   "`, `"﻿"`, a number, `null` or missing are each named with the fix; a
    description with words is valid;
  - a milestone with a bad title and an empty description gets a message for each, and one bad milestone doesn't hide
    another's problem;
  - the existing rules don't crash on a milestone with a missing or non-string field.

  Verify they fail before 1.3 for the right reason: a missing problem or a crash, not a typo in the test.
- [x] 1.3 Add the shape function and the new rules to `declaration_problems`, and make the existing rules skip a
  missing or non-string field (design D3). Add the comment pointing at the website's `readRoadmap` and its design D4,
  saying a rule changed here must change there too (design D4), and update the module and function docstrings. Verify
  the tests from 1.2 and every existing test pass.
- [x] 1.4 Make the test that reads the real file check its shape first and parse it with a `parse_constant` that
  refuses `NaN`, `Infinity` and `-Infinity` (design D1, D3), and add a test that a file with `NaN` fails naming
  `tofu/milestones.json`. Verify `test_the_declared_milestones_are_well_formed` passes on today's file, and fails,
  naming the milestone, when a title in a scratch copy is changed to `v0.3.0` (run it against the copy, then discard
  it; `tofu/milestones.json` stays unchanged).

## 2. The rules, checked against the website

- [ ] 2.1 Run the website's `readRoadmap` (troupe-run/website `origin/main`, `scripts/roadmap-lib.mjs`) with `node`
  on each case from 1.2 and 1.4, each wrapped in a minimal file, and compare its verdict (accept or refuse) with this
  check's (design D1). Keep the script in the scratchpad, not in the repository. Verify every case agrees, except the
  `\x1c`–`\x1f`/`\x85` description that design D1 accepts as stricter here; record the result in this task's note.
  Any other disagreement is either a fix to 1.3 or, if the website is wrong, a question for the owner before going on.

## 3. Integration

- [ ] 3.1 Verify `uv run scripts/check.py` passes in full, and `uv run scripts/check.py --scope milestones` passes too,
  since that's what the `check` job runs for a pull request that changes only `tofu/milestones.json`.
- [ ] 3.2 Open the pull request with `Closes #125`, using `--body-file`, with 2.1's comparison in the body. Verify the
  required checks pass, and that the `tofu` workflow decides no plan is needed (the change touches only
  `scripts/tests/` and `openspec/`).

## Workflow follow-up

- Archive the change on the branch before the owner merges, and rebase onto `origin/main` if it has moved.
- After the merge, check #125 is closed and its card says Done. Comment on it with the PR and the archived change, say
  that the website's `scripts/roadmap-lib.mjs` doesn't yet point back at this check, and leave that to the website's
  owner (design D4).
- Delete the worktree and branch once the merge is verified.
