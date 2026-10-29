# Tasks

## 1. Pin what must not change

- [x] 1.1 Before touching `scripts/guard.py` or `scripts/dependabot_issues.py`, add a test in
  `scripts/tests/test_guard_dependabot.py` that runs every existing bump fixture (ZOD, POSTCSS, AXE, TYPESCRIPT,
  EVENTSOURCING, DOWNLOAD_ARTIFACT) through `run_ci` on a reserved branch and records each outcome (pass, or the
  refusal's reason). Run it on the unchanged code and verify it passes, so a later change to a bump's result fails it
  (design D2: no version bump's result changes)

## 2. One counting for ranges (design D4)

- [x] 2.1 In `scripts/dependabot_issues.py`, add the pair counting (each pair counted with `update_type`, a pair that
  goes down makes it unknown, the largest kind wins, no differing pair is unknown) and `range_kind(old, new)` (split on
  commas and spaces, operator plus `VERSION`, same operators each once, paired by operator). Use it in `read_update`
  for a requirement title. Add tests to `scripts/tests/test_dependabot_issues.py` for #181's real title (patch),
  `Update jsonschema requirement from <5,>=4.26 to >=4.26,<6` (major), a lowered bound, an operator added or dropped,
  and an `x` wildcard (unknown), and verify they pass
- [x] 2.2 Update `issue_body`'s tests so a requirement title counted patch or minor gets no "needs an OpenSpec change"
  line, and one counted major or unknown still does (spec: `dependency-updates`, "The issue says what the update
  is"); verify they pass
- [x] 2.3 Copy the pair counting and `range_kind` into `scripts/guard.py` with docstrings naming the original, and
  add `DEPENDABOT_REQUIREMENT`, the requirement-subject pattern (D2), to both files. Extend
  `test_the_guard_s_copies_are_the_issue_workflow_s_patterns` to compare it, and add a property test that generates
  version pairs and ranges and asserts the guard's and the issue's `range_kind` agree; verify both pass

## 3. Reading a requirement commit from its diff (design D3, D5)

- [ ] 3.1 Add a real troupe #181 fixture: its commit message as Dependabot wrote it (`dependency-version: 0.13.3`),
  base `pyproject.toml` files holding `requires = ["uv_build>=0.13.0,<0.14"]`, and the commit changing them to
  `>=0.13.5,<0.14` on `dependabot/uv/uv-build-gte-0.13.3-and-lt-0.14` in `troupe-run/troupe`. Rename and rewrite
  `test_a_requirement_range_fails_saying_its_versions_can_t_be_read` into a test that this branch passes `run_ci`
  (spec scenario "A requirement range"), and verify it fails on the current code
- [ ] 3.2 Implement D3 in `dependabot_ineligibility`: a commit matching `DEPENDABOT_REQUIREMENT` is read from its
  manifest lines (steps 1-5), with D5's reasons. Verify 3.1's test and 1.1's pin pass
- [ ] 3.3 Add a test per spec scenario of "A Dependabot requirement update is read from the manifest lines it
  changes": an upper bound raised a minor step with `uv.lock` changed (passes), a range admitting a new major (refused,
  major), a lowered bound, a line changing more than versions, a line for another dependency (`pydantic` under a
  `uv-build` subject), only `uv.lock` changed (each refused with its D5 reason and the line), and a near-name line
  (`uv-build-extra` under `uv-build`, refused). Verify each fails before its part of 3.2 exists or by mutation (break
  the step and see it fail), then passes
- [ ] 3.4 Add D3 step 6: a long requirement subject whose ranges' kind differs from the diff's is refused, naming both
  kinds; one that agrees passes. Test both and verify they pass
- [ ] 3.5 Add the differential test of D4: generate ranges, render a `pyproject.toml` line pair and a title (old
  specifiers shuffled), and assert the guard's diff reading of a commit and `dependabot_issues.read_update` of the
  title give the same kind. Verify it passes, and fails if the guard's pair counting is changed to ignore direction
- [ ] 3.6 Update `test_the_real_subjects_kinds` for #181's title (both readers now say patch) and verify the file's
  tests pass

## 4. Docs and checks

- [ ] 4.1 Rewrite the two Dependabot bullets in `docs/development-workflow.md`: a requirement update is read from the
  manifest lines it changes, exempt when only version numbers of its dependency go up a minor or patch step; a range
  admitting a new major, a lowered bound, or a line changing more than versions takes an OpenSpec change. Verify the
  section no longer gives `Update uv-build requirement` as an unreadable example
- [ ] 4.2 Run `uv run scripts/check.py` (ruff, mypy --strict, pytest, OpenSpec strict validation including this
  change) and verify it passes
- [ ] 4.3 Run a local plan (fast-forward onto `origin/main` first) and verify it changes only the delivered
  `scripts/guard.py` in troupe and website

## Workflow follow-up

- Open the pull request closing #220; the owner approves the plan run; act on Claude's review of the last push.
- Archive on the branch before the merge; the owner merges by rebase.
- After the apply, comment `@dependabot rebase` on troupe #181 (or ask the owner to) and verify its `guard` run passes
  on the new head; comment on troupe #179 that the update now reads as a patch and takes the light path.
- Comment on #220 with the pull request and the archived change; check the issue is closed and its card is Done.
