# Tasks

## 1. The resolving step (design D2, D3)

- [x] 1.1 In `scripts/tests/test_claude_review_workflow.py`, rename `test_only_the_review_s_open_must_fixes_are_resolved`
  to `test_only_the_review_s_open_must_fixes_and_nits_are_resolved` and expect `PRRT_mustfix`, `PRRT_upgraded`,
  `PRRT_downgraded`, `PRRT_nit` and `PRRT_selflabel` resolved, with a warning naming each of the other five. Verify it fails against the
  current step (only the two must-fixes resolved)
- [x] 1.2 In `claude-review.yml`'s "Resolve and re-tier what Claude named", accept a tier of must-fix or nit (a fixed
  tuple, not "anything but decision"), and change the skip warning to say only a must-fix or a nit is the review's to
  resolve. Update the step's pinned hash and the `if False:` case of `test_each_way_the_workflow_can_go_wrong_is_named`
  for the new line, and add a named case where `"decision"` joins the allowed tiers. Verify `uv run pytest
  scripts/tests/test_claude_review_workflow.py` passes, including 1.1's test

## 2. The prompt and the workflow's comments (design D1)

- [x] 2.1 Add a test that the review's prompt doesn't say "Never resolve a decision or a nit", tells Claude to name
  a nit in `resolve` only when the diff shows its problem gone (a reply alone doesn't), and still says never to
  resolve a decision or anyone else's conversation. Verify it fails on the current prompt
- [x] 2.2 Change the prompt as D1 describes: the nit tier's "The author resolves these" gains "or you do once a push
  has fixed one", and the list for each open conversation gains the nit item. Update the file's header comment and the
  `resolve` step's comment to say the job resolves the review's must-fixes and the nits a push fixed. Verify 2.1's
  test passes and `uv run scripts/check.py` passes

## 3. Docs and the delivered summary (design D4)

- [x] 3.1 In `docs/development-workflow.md`, "Claude's review": the nit row's "Who resolves it" adds the review, on the
  run for the push that fixed it, and the paragraph on replies says a nit fixed by a push needs no reply or resolve.
  Say the same in `CLAUDE.md` step 5, `openspec/config.yaml`'s context, and `org-profile/CONTRIBUTING.md` step 4.
  Verify with `grep -n -i "nit" ` over the four files, reading each hit, and `uv run scripts/check.py`
- [x] 3.2 Change `WORKFLOW_SUMMARY` in `scripts/guard.py` to say the review resolves the must-fixes and the nits a push
  fixed, keeping it ASCII. Verify by running the session-start hook (`uv run scripts/guard.py` as the hook calls it)
  and reading its `additionalContext`, and `uv run scripts/check.py`
- [ ] 3.3 Run website's `npx vitest run tests/unit/workflow-node-version.test.ts` and troupe's `uv run
  scripts/check.py` with the new `claude-review.yml` and `scripts/guard.py` in place in scratch clones, as the
  workflow's header asks; verify both pass

## 4. troupe and website (design D4)

- [ ] 4.1 Raise an issue in troupe-run/troupe and one in troupe-run/website (each with `--project "troupe roadmap"`)
  to say in their `CLAUDE.md` and `openspec/config.yaml` that the review resolves a nit a push has fixed, citing #246
  and the development-workflow requirement. Verify each with `gh issue view <n> -R troupe-run/<repo> --json
  projectItems`, and link both in a comment on #246

## 5. Plan

- [ ] 5.1 Check the pull request's `plan (pull request)` shows the two deliveries of `claude-review.yml`, the two of
  `scripts/guard.py`, and `CONTRIBUTING.md` in troupe-run/.github, and nothing else. Record its run and counts here

## Workflow follow-up

- Open the draft pull request (`Closes #246`), act on Claude's review, mark it ready; the owner approves
  `plan (pull request)`.
- Archive on the branch before merging (batch the archive with the last tick and a rebase onto main's state commit,
  so the plan is approved once).
- After the merge and the owner's apply: a new pull request event on website#87 (its owning session rebases it onto
  main) runs the delivered review; check its `resolve` job resolves the `/\host` nit, and record the run on #246. If
  #87 has merged by then, use a pull request whose nit a later push fixes.
- Comment on #246 with the PR, the archived change and that run; check it's closed and its card says Done.
