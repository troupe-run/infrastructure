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
- [x] 1.4 Open a draft pull request with `Closes #375`, using `--body-file`, and act on Claude's review. Verify the
  review of the last push completed with no must-fix or decision open.
  Done: #376. Claude's review of d0b6c6e had no findings. No local plan was run: it needs a 1Password approval that
  timed out on 2026-11-20, and since #261 CI's plan is the evidence (orchestrator, 2026-11-20). That plan is checked on
  the final head, after this archive, under "Workflow follow-up" (owner, 2026-11-20: one plan-pr approval, on the
  final head).

## 2. Outcomes for the issues with no milestone

- [x] 2.1 Comment on #375 with the list of open issues with no milestone
  (`gh issue list -R troupe-run/<repo> --state open --search no:milestone`), one line per issue, and ask the owner
  (through the orchestrator) for each one's outcome: into a milestone (which), `parked` (with the reason to come back),
  or closed as not planned. Verify the comment is on #375.
  Done: issuecomment-7036440321 lists 54 (troupe 25, infrastructure 25 with #375, website 4; `.github` left out as its
  issues are off), with a link fix in issuecomment-7036445312.
- [x] 2.2 Carry out each outcome the owner gives, at their word: set the milestone, add the `parked` label with a
  comment giving the reason, or `gh issue close <n> -R troupe-run/<repo> --reason "not planned" --comment "<why>"`.
  Verify by re-running the 2.1 query: what it still lists is only issues the owner parked or kept open.
  Done: troupe 486, 418, 419, 456 and 299 are in 0.3.0. The REST list of open issues with no milestone now reads
  troupe 20, infrastructure 25, website 4: the 49 kept parked, kept open until decided, kept as upkeep, and #375.
- [x] 2.3 Record the outcomes on #375 in one comment: each issue, its outcome, and the owner's reason where given.
  Verify every issue from 2.1's list appears in it.
  Done: issuecomment-7036573915 accounts for all 54 (5 into 0.3.0, 9 parked, 5 decisions, 34 upkeep, #375). None
  closed as not planned.

## Workflow follow-up

- Act on Claude's review of the last push, then archive the change on the branch in the same push as ticking 1.4 and
  2.3, and rebase onto `main`'s latest state commit before asking for the plan approval.
- Before the merge, on the final head's plan-pr run: check the plan is `0 to add, 4 to change, 0 to destroy`,
  milestone 0.2.0 in each of troupe, infrastructure, website and `.github`, each changing only `state` to `closed`.
  Check its list of issues with no milestone matches 2.2's 49 (or what the query lists then), leaves `.github` out
  saying why, and doesn't read "none". Post both on #375.
- When the plan of `main` runs, compare its list with 2.3's record. Any issue opened since gets an outcome from the
  owner, added to #375's record, before the owner approves the apply.
- After the apply, check on GitHub that milestone 0.2.0 is closed in all four repositories
  (`gh api 'repos/troupe-run/<repo>/milestones?state=all'`), still holds its closed issues, and that the next drift
  check is green.
- Check that the merge dispatched a website Deploy run on `main`, and once it has finished, that troupe.run/status/
  shows 0.2.0 under its released versions.
- Check #375 is closed with a comment naming the pull request and the archived change, and its card says Done.
