# Tasks

## 1. Close 0.3.0

- [x] 1.1 Wait for `troupe-run-v0.3.0`'s release, and its install check passing on all twelve platform and Python
  legs. Verify with `gh run view <id> -R troupe-run/troupe --json jobs` for the `release install check` run of that
  release: every `install (...)` job succeeded. If one fails, file a Bug on the board and stop.
  Done: troupe-run/troupe#516 merged 2026-11-24 21:41Z; `troupe-run-v0.3.0` published (release run 45493675730,
  "Creating 1 releases"); install check 45493715020 passed on all 12 legs.
- [x] 1.2 Rebase this branch onto `origin/main` after its latest state commit. Verify
  `git rev-list --count HEAD..origin/main` is 0.
- [x] 1.3 Check 0.3.0 is still empty of open issues. Verify
  `gh issue list -R troupe-run/<repo> --milestone 0.3.0 --state open` lists nothing for troupe, infrastructure and
  website. If one has appeared, stop and ask the owner.
- [x] 1.4 In `tofu/milestones.json`, change the `state` of the entry titled 0.3.0 (key `0.2.0`) from `open` to
  `closed`, and rename `test_today_s_release_in_progress_is_0_3_0` to `..._is_0_4_0`, asserting `0.4.0`. Verify
  `git diff` changes only those, and `uv run scripts/check.py` passes.
  Done: check passed (4062 passed, 26 skipped).
- [x] 1.5 Open a draft pull request with `Closes #401`, using `--body-file`, and act on Claude's review. Verify the
  review of the last push completed with no must-fix or decision open. No local plan: CI's plan is the evidence
  (#261), checked on the final head under "Workflow follow-up".
  Done: #403. Claude's review of 6b3c5b5 had no findings.

## 2. Outcomes for the issues with no milestone

- [x] 2.1 Comment on #401 with the list of open issues with no milestone
  (`gh issue list -R troupe-run/<repo> --state open --search no:milestone`), grouped, one line per issue, marking
  those #375 already gave an outcome. Ask the owner (through the orchestrator) for each one's outcome: into a milestone
  (which), `parked` (with the reason to come back), or closed as not planned. Verify the comment is on #401.
  Done: issuecomment-7144799808 lists 66 (troupe 28, infrastructure 29, website 9; `.github` left out as its issues
  are off): 45 with #375's outcomes still open, 21 new.
- [x] 2.2 Carry out each outcome the owner gives, at their word: set the milestone, add the `parked` label with a
  comment giving the reason, or `gh issue close <n> -R troupe-run/<repo> --reason "not planned" --comment "<why>"`.
  Verify by re-running the 2.1 query: what it still lists is only issues the owner parked or kept open.
  Done: troupe-run/troupe#506 is in 0.4.0. The query now lists troupe 27, infrastructure 30 (with #401), website 9:
  the 65 kept and #401.
- [x] 2.3 Record the outcomes on #401 in one comment: each issue, its outcome, and the owner's reason where given.
  Verify every issue from 2.1's list appears in it.
  Done: issuecomment-7144843344 (owner, 2026-11-25) accounts for all 66: 1 into 0.4.0, 45 keep #375's outcomes (9
  parked, 5 decisions, 31 upkeep), 20 new upkeep. None closed as not planned.

## Workflow follow-up

- Act on Claude's review of the last push, then archive the change on the branch, and rebase onto `main`'s latest
  state commit before asking for the plan approval.
- Before the merge, on the final head's plan-pr run: check the plan is `0 to add, 4 to change, 0 to destroy`,
  milestone 0.3.0 in each of troupe, infrastructure, website and `.github`, each changing only `state` to `closed`.
  Check its list of issues with no milestone matches 2.2's (or what the query lists then), leaves `.github` out saying
  why, and doesn't read "none". Post both on #401.
- When the plan of `main` runs, compare its list with 2.3's record. Any issue opened since gets an outcome from the
  owner, added to #401's record, before the owner approves the apply.
- After the apply, check on GitHub that milestone 0.3.0 is closed in all four repositories
  (`gh api 'repos/troupe-run/<repo>/milestones?state=all'`), still holds its closed issues, and that the next drift
  check is green.
- Check that the merge dispatched a website Deploy run on `main`, and once it has finished, that troupe.run/status/
  shows 0.3.0 under its released versions.
- Check #401 is closed with a comment naming the pull request and the archived change, and its card says Done.
