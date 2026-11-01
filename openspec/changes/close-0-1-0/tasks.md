# Tasks

## 1. Close 0.1.0

- [x] 1.1 Rebase this branch onto `origin/main` after its latest state commit. Verify
  `git rev-list --count HEAD..origin/main` is 0.
- [x] 1.2 Check 0.1.0 is still empty of open issues. Verify
  `gh issue list -R troupe-run/<repo> --milestone 0.1.0 --state open` lists nothing for troupe, infrastructure and
  website. If one has appeared, stop and ask the owner.
- [x] 1.3 In `tofu/milestones.json`, change 0.1.0's `state` from `open` to `closed`. Verify `git diff` changes only that
  line and `uv run scripts/check.py` passes.
  Added: `test_today_s_release_in_progress_is_0_1_0` pins today's release in progress, which this moves to the
  milestone titled 0.2.0, so it's renamed `..._is_0_2_0` and asserts `0.2.0`.
- [x] 1.4 Run a local plan. Verify it shows four updates in place, milestone 0.1.0 in each of troupe, infrastructure,
  website and `.github`, each changing only `state` to `closed`, and nothing created, destroyed or replaced.
- [x] 1.5 Run `scripts/milestone_review.py` locally the way the `tofu` workflow does for a plan that closes a
  milestone. Verify it says 0.1.0 closes, lists the open issues with no milestone for troupe, infrastructure and
  website with their count, and leaves `.github` out saying why. Compare its count with
  `gh issue list -R troupe-run/<repo> --state open --search no:milestone`.
  Done: the local plan of d7bac5b is "0 to add, 4 to change, 0 to destroy", 0.1.0's `state` open -> closed in
  `.github`, infrastructure, troupe and website. The list has 17 issues (troupe 7, infrastructure 5, website 5,
  `.github` left out as its issues are off), the same numbers the query gives. #244 is one of them.
- [ ] 1.6 Open a draft pull request with `Closes #244`, using `--body-file`. Verify the CI plan comment, once the pull
  request is ready and its plan has run, shows the same four updates as 1.4 and the same list as 1.5 (as it is then).

## 2. Outcomes for the issues with no milestone

- [ ] 2.1 Comment on #244 with the plan comment's list, one line per issue, and ask the owner for each one's outcome:
  into a milestone (which), `parked` (with the reason to come back), or closed as not planned. Ask with
  AskUserQuestion, not by assuming (memory: ask open decisions directly). Verify the comment is on #244.
- [ ] 2.2 Carry out each outcome the owner gives, at their word: set the milestone, add the `parked` label with a
  comment giving the reason, or `gh issue close <n> -R troupe-run/<repo> --reason "not planned" --comment "<why>"`.
  Verify every listed issue now has a milestone, the `parked` label, or is closed, by re-running the 1.5 query: what
  it still lists is only issues the owner parked.
- [ ] 2.3 Record the outcomes on #244 in one comment: each issue, its outcome, and the owner's reason where given.
  Verify every issue from 2.1's list appears in it.

## Workflow follow-up

- Act on Claude's review of the last push, then archive the change on the branch in the same push as ticking 1.6 and
  2.3, and rebase onto `main`'s latest state commit before asking for the plan approval (memory: archive before plan
  approval).
- When the plan of `main` runs, compare its list with 2.3's record. Any issue opened since gets an outcome from the
  owner and is added to #244's record before the owner approves the apply.
- After the apply, check on GitHub that milestone 0.1.0 is closed in all four repositories
  (`gh api 'repos/troupe-run/<repo>/milestones?state=all'`), still holds its closed issues, and that the next drift
  check is green.
- Check that the merge dispatched a website Deploy run on `main`, and once it and the apply have finished, that
  troupe.run/status/ shows 0.1.0 under its released versions. If the deploy ran before the apply finished, ask the
  owner to run `gh workflow run deploy.yml -R troupe-run/website`.
- Check #244 is closed with a comment naming the pull request and the archived change, and its card says Done.
