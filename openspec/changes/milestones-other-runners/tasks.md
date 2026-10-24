# Tasks

## 1. Start from #129's apply

- [ ] 1.1 Check #129 is merged and applied: its state commit is on `origin/main`. Rebase this branch onto it. Verify
  `git rev-list --count HEAD..origin/main` is 0.
- [ ] 1.2 Verify on GitHub that each of the four managed repositories has the 13 interim titles and the 8 unchanged
  titles, and nothing else (`gh api repos/troupe-run/<repo>/milestones?state=all`). Save each milestone's number,
  title and open and closed counts, per repository, as the snapshot for 3.1, in the scratchpad.

## 2. The final titles

- [ ] 2.1 Remove the 13 `interim_title` fields from `tofu/milestones.json` (design D1). Verify `uv run scripts/check.py`
  passes and `git diff` changes only those lines.
- [ ] 2.2 Run a local plan. Verify it shows 52 updates in place, 13 in each of the four repositories, each changing
  only the title from `<version> (renumbering)` to `<version>`, and nothing created, destroyed or replaced.
- [ ] 2.3 Open the pull request with `Closes #128`, using `--body-file`. Verify the CI plan comment shows the same
  counts as 2.2.

## Workflow follow-up

- Archive the change on the branch in the same push as ticking 2.3, and rebase onto `main`'s latest state commit
  before asking for the plan approval (memory: archive before plan approval).
- After the owner merges and approves the apply, check the result (design D2): in every repository, the milestones
  titled 0.2.0 and 0.3.0 have the numbers that 1.2 recorded for keys `0.14.0` and `0.2.0`, and every milestone's
  counts match 1.2's snapshot. In troupe, 0.2.0 (milestone 20) holds #56 and #162, and 0.3.0 (milestone 3) holds #5,
  #45, #119 and #138.
- Rebuild /status/ (design D3): if no website deploy has run since #129 merged, ask the owner to run
  `gh workflow run deploy.yml -R troupe-run/website`. Check troupe.run/status/ lists 0.1.0, 0.2.0 "Other runners",
  0.3.0 "Config by hand", up to 0.14.0 "Contained", then 0.15.0 to 1.0.0.
- Comment on troupe-run/troupe#139: the renumbering is applied (#129, #128), and milestone changes here don't
  trigger a website build, so /status/ shows them at its next deploy.
- Check #128 is closed with a comment naming the PR and the archived change, and its card says Done.
