# Tasks

## 1. Close 0.2.0

- [x] 1.1 Rebase this branch onto `origin/main` after its latest state commit. Verify
  `git rev-list --count HEAD..origin/main` is 0.
- [x] 1.2 Check 0.2.0 is still empty of open issues. Verify
  `gh issue list -R troupe-run/<repo> --milestone 0.2.0 --state open` lists nothing for troupe, infrastructure and
  website. If one has appeared, stop and ask the owner.
- [x] 1.3 In `tofu/milestones.json`, change the `state` of the entry titled 0.2.0 (key `0.14.0`) from `open` to
  `closed`, and rename `test_today_s_release_in_progress_is_0_2_0` to `..._is_0_3_0`, asserting `0.3.0`. Verify
  `git diff` changes only those, and `uv run scripts/check.py` passes.
- [ ] 1.4 Check the plan shows four updates in place, milestone 0.2.0 in each of troupe, infrastructure, website and
  `.github`, each changing only `state` to `closed`, and nothing created, destroyed or replaced. Verified on the pull
  request's CI plan (1.6), not a local plan: a local plan needs a 1Password approval that timed out on 2026-11-20, and
  since #261 CI's plan is the real evidence (orchestrator, 2026-11-20, choosing the recommended option).
- [ ] 1.5 Compare CI's list of open issues with no milestone (1.6) with
  `gh issue list -R troupe-run/<repo> --state open --search no:milestone` for troupe, infrastructure and website. Verify
  the counts match, `.github` is left out saying why, and record both on #375. On 2026-11-20 the query lists troupe 25,
  infrastructure 25 (#375 among them) and website 4.
- [ ] 1.6 Open a draft pull request with `Closes #375`, using `--body-file`. Verify the CI plan comment, once the pull
  request is ready and its plan has run, shows the same four updates as 1.4 and the same list as 1.5 (as it is then;
  since #261 it should not read "none").

## 2. Outcomes for the issues with no milestone

- [ ] 2.1 Comment on #375 with the list, one line per issue, and ask the owner (through the orchestrator) for each
  one's outcome: into a milestone (which), `parked` (with the reason to come back), or closed as not planned. Verify
  the comment is on #375.
- [ ] 2.2 Carry out each outcome the owner gives, at their word: set the milestone, add the `parked` label with a
  comment giving the reason, or `gh issue close <n> -R troupe-run/<repo> --reason "not planned" --comment "<why>"`.
  Verify by re-running the 1.5 query: what it still lists is only issues the owner parked or kept open as upkeep.
- [ ] 2.3 Record the outcomes on #375 in one comment: each issue, its outcome, and the owner's reason where given.
  Verify every issue from 2.1's list appears in it.

## Workflow follow-up

- Act on Claude's review of the last push, then archive the change on the branch in the same push as ticking 1.6 and
  2.3, and rebase onto `main`'s latest state commit before asking for the plan approval.
- When the plan of `main` runs, compare its list with 2.3's record. Any issue opened since gets an outcome from the
  owner, added to #375's record, before the owner approves the apply.
- After the apply, check on GitHub that milestone 0.2.0 is closed in all four repositories
  (`gh api 'repos/troupe-run/<repo>/milestones?state=all'`), still holds its closed issues, and that the next drift
  check is green.
- Check that the merge dispatched a website Deploy run on `main`, and once it has finished, that troupe.run/status/
  shows 0.2.0 under its released versions.
- Check #375 is closed with a comment naming the pull request and the archived change, and its card says Done.
