# Tasks

## 0. The owner's decisions and the issue

- [x] 0.1 Owner: confirm design D3 (the forms stay as they are) and D4 (no enforcement in this change). If they want
      either, open the follow-up issue on the board (`gh issue create -R troupe-run/infrastructure --project "troupe
      roadmap"`), with a type and an "Arose from troupe-run/infrastructure#149." line, and verify it shows with
      `gh issue view <n> -R troupe-run/infrastructure --json projectItems`. If the owner wants a form or a check in
      this change, update the change first (`/opsx:update`). Done (owner, 2026-10-28, asked directly): the forms stay
      as they are, and nothing enforces the rule for now, so no follow-up issue is opened
- [x] 0.2 Verify #149's card says In Progress with `gh issue view 149 -R troupe-run/infrastructure --json
      projectItems`, and set it if it doesn't. Done: In Progress (2026-10-28)

## 1. The issue-type test (design D2)

- [x] 1.1 Add D2's function and its tests to `scripts/tests/test_org_profile.py`: the real-guide test, and fixture
      tests for a sound list, a type the org lacks (Chore), a type the guide leaves out (Task), and no list. Verify
      the fixture tests pass, and the real-guide test fails against the current guide, saying the list wasn't found.
      Done: the 4 fixture tests pass, and the real-guide test failed with "the guide's list of issue types wasn't
      found"

## 2. The guide (design D1)

- [x] 2.1 Add D1's `## How issues are related` section to `org-profile/CONTRIBUTING.md`, straight before
      `## Milestones`. Verify the real-guide test from 1.1 now passes, that dropping `Task` from the list makes it
      fail naming Task, and that adding `Chore` makes it fail naming Chore (revert both). Done: it passes,
      then fails naming Task, then Chore; both reverted
- [x] 2.2 Make D1's two smaller edits: the sentence in "How work flows" step 1, and the link from the Milestones
      section's "the work it arose from" to `#how-issues-are-related`. Verify with `git diff` that the source note is
      still the first line and that no other section changed, and, once the pull request is open, that the anchor
      resolves in GitHub's rendering of the file on the branch. Done: the diff leaves the note and other sections
      alone, and on #214's branch GitHub renders `id="user-content-how-issues-are-related"` with the link to it
- [x] 2.3 Run `uv run scripts/check.py` and `openspec validate issue-relationships-rule --strict`, and verify both
      pass. Done: "check: all gates passed" and "Change 'issue-relationships-rule' is valid"

## 3. The review and the plan

- [x] 3.1 Act on Claude's review of the last push: fix or answer each must-fix and nit, resolve only nits, and raise
      each decision, and each must-fix in dispute, with the owner. Verify no review conversation is left open with
      `gh pr view <n> -R troupe-run/infrastructure --json reviewDecision` and the pull request's conversations. Done:
      one must-fix (2.2 unticked), fixed by 318bb28 and resolved by `troupe-run-review[bot]`; the re-review of
      318bb28 found nothing new, and no conversation on #214 is open
- [x] 3.2 Once the owner approves the pull request's `plan-pr` run, read its plan comment and verify it reads
      `0 to add, 1 to change, 0 to destroy`, the one change being
      `github_repository_file.org_profile["CONTRIBUTING.md"]`. If it shows anything else, stop and find out why. Tick
      this in the same push as the archive, rebased onto `main`'s state commit, so the owner approves one more run.
      Done: #214's plan for 318bb28 reads `Plan: 0 to add, 1 to change, 0 to destroy.`, the one change being
      `github_repository_file.org_profile["CONTRIBUTING.md"]` updated in place

## Workflow follow-up

- Open the pull request with `Closes #149`. Its plan comment is 3.2's evidence.
- Archive the change on the branch before the second `plan-pr` approval, in the same push as 3.2's tick.
- The owner merges by rebase and approves the `apply` job of `main`'s plan. Verify
  `gh api repos/troupe-run/.github/contents/CONTRIBUTING.md --jq .content | base64 -d | diff - org-profile/CONTRIBUTING.md`
  prints nothing, and the new section's link works on GitHub.
- Comment on #149 with the pull request and the archived change, check it's closed, and check its card says Done.
