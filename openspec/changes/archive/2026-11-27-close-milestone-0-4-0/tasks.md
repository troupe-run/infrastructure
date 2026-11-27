# Tasks

## 1. Close 0.4.0

- [x] 1.1 Wait for `troupe-run-v0.4.0`'s release, and for its install check to pass on all twelve platform and Python
  legs. Verify with `gh run view <id> -R troupe-run/troupe --json jobs` for the `release install check` run of that
  release: every `install (...)` job succeeded. A macOS leg cancelled for runner capacity is re-run, not a failure. If
  a leg fails, file a Bug on the board and stop.
  Done: troupe-run/troupe#541 merged 2026-11-27; `troupe-run-v0.4.0` published (release run 45948621807, "Creating 1
  releases"). Install check 45948648669: macOS / 3.12 failed to connect to github.com:443 on attempt 1; the re-run of
  that leg passed, so all 12 legs are green. Its Bug, troupe-run/troupe#542, was closed with that run.
- [x] 1.2 Rebase this branch onto `origin/main` after its latest state commit. Verify
  `git rev-list --count HEAD..origin/main` is 0.
  Done: rebased onto d3fb77c.
- [x] 1.3 Check 0.4.0 is still empty of open issues. Verify
  `gh issue list -R troupe-run/<repo> --milestone 0.4.0 --state open` lists nothing for troupe, infrastructure and
  website. If one has appeared, stop and ask the owner.
  Done: 0 open in troupe, infrastructure and website.
- [x] 1.4 In `tofu/milestones.json`, change the `state` of the entry titled 0.4.0 (key `0.3.0`) from `open` to
  `closed`. Rename `test_today_s_release_in_progress_is_0_4_0` to `..._is_0_5_0`, asserting `0.5.0`. Verify
  `git diff` changes only those, and `uv run scripts/check.py` passes.
  Done: see the commit's check.
- [x] 1.5 Open a draft pull request with `Closes #423`, using `--body-file`, and act on Claude's review. Verify that the
  review of the last push completed with no must-fix or decision open. No local plan: CI's plan is the evidence
  (#261), checked on the final head under "Workflow follow-up".
  Done: #424. Claude's review of 6440bb5 had no findings.

## 2. Outcomes for the issues with no milestone

- [x] 2.1 Comment on #423 with the list of open issues with no milestone
  (`gh issue list -R troupe-run/<repo> --state open --search no:milestone`), grouped, one line per issue, marking
  those that #401 already gave an outcome. Ask the owner (through the orchestrator) for each one's outcome: into a
  milestone (which), `parked` (with the reason to come back), or closed as not planned. Verify the comment is on #423.
  Done: issuecomment-7210783083 lists 62 (troupe 29, infrastructure 27, website 6; `.github` left out): 49 with
  #401's outcomes still open, 12 new, and #423.
- [x] 2.2 Carry out each outcome the owner gives, at their word: set the milestone, add the `parked` label with a
  comment giving the reason, or `gh issue close <n> -R troupe-run/<repo> --reason "not planned" --comment "<why>"`.
  Verify by re-running the 2.1 query: what it still lists is only issues the owner parked or kept open.
  Done: nothing to carry out. The owner kept all 12 new issues open with no milestone (2026-11-27).
- [x] 2.3 Record the outcomes on #423 in one comment: each issue, its outcome, and the owner's reason where given.
  Verify every issue from 2.1's list appears in it.
  Done: issuecomment-7210849476 (owner, 2026-11-27) accounts for all 62: 49 keep #401's outcomes, 12 new upkeep
  (#414 open until decided), #423 closed by the PR. None into a milestone, none closed as not planned.

## Workflow follow-up

- Act on Claude's review of the last push, then archive the change on the branch. Rebase onto `main`'s latest
  state commit before asking for the plan approval.
- Before the merge, on the final head's plan-pr run, check the plan is `0 to add, 4 to change, 0 to destroy`:
  milestone 0.4.0 in each of troupe, infrastructure, website and `.github`, each changing only `state` to `closed`.
  Check that its list of issues with no milestone matches 2.2's (or what the query lists then), leaves `.github` out
  saying why, and doesn't read "none". Post both on #423.
- When the plan of `main` runs, compare its list with 2.3's record. Any issue opened since then gets an outcome from
  the owner, added to #423's record, before the owner approves the apply.
- After the apply, check on GitHub that milestone 0.4.0 is closed in all four repositories
  (`gh api 'repos/troupe-run/<repo>/milestones?state=all'`), still holds its closed issues, and that the next drift
  check is green.
- Check that the merge dispatched a website Deploy run on `main`. Once it has finished, check that troupe.run/status/
  shows 0.4.0 under its released versions.
- Check #423 is closed with a comment naming the pull request and the archived change, and that its card says Done.
