# Tasks

## 1. Declare the milestones

- [x] 1.1 Rewrite `tofu/milestones.json`'s `milestones` as design D1 says: the 21 milestones in release order, each with
      `key` equal to `title`, state `open`, and #119's description word for word, keeping the keys `0.1.0`, `0.2.0` and
      `1.0.0`. Verify with `jq -r '.milestones[] | [.key, .title, .state] | @tsv'` that there are 21 rows in order and
      every key equals its title, compare each description with #119's table (`gh issue view 119 --json body`), and
      check `git diff` leaves `repositories` unchanged
- [x] 1.2 Update `README.md`'s milestones row as design D4 says. Verify `grep -rn "0\.2\.0, 1\.0\.0" README.md docs` finds
      nothing, and that `uv run scripts/check.py` passes (including `scripts/tests/test_milestones.py`)
- [x] 1.3 Add design D6's Milestones section to `org-profile/CONTRIBUTING.md`, after "How work flows". Verify the
      source note is still the file's first line, `git diff` shows only the added section, and
      `uv run scripts/check.py` passes
- [x] 1.4 Run `uv run scripts/oob.py` and verify its milestones section reports nothing (every title on GitHub is
      already declared; the new ones just aren't created yet)
- [x] 1.5 Run `openspec validate roadmap-milestones --strict` and verify it passes

## 2. Verify the plan

- [ ] 2.1 Once the owner approves the pull request's first `plan-pr` run, read its plan comment and verify the summary
      reads `72 to add, 13 to change, 0 to destroy`, 12 of the changes are `description` only on `0.1.0`, `0.2.0`
      and `1.0.0` in each of the four repositories, the 13th is `.github`'s `CONTRIBUTING.md`, and the 72 adds are
      `0.3.0` to `0.20.0` in each (design D2). If it shows anything else, stop and fix the declaration. Tick this in the same push as the archive, rebased onto
      `main`'s state commit, so the owner approves one more run

## Workflow follow-up

- Open the pull request with `Closes #119`, design D3's tables, and the release-please note from design's Risks. Its
  plan comment is 2.1's evidence. Before the second `plan-pr` approval, archive the change and rebase onto `main`'s
  state commit in one push.
- The owner merges by rebase. After the merge, the owner reads the `plan (main)` plan and approves the `apply` job.
  Verify with `gh api "repos/troupe-run/<repo>/milestones?state=all&per_page=100" --jq '.[] | [.title, .description] | @tsv'`
  for each of troupe, infrastructure, website and `.github` that each has the 21 milestones with the declared
  descriptions, and that 0.1.0, 0.2.0 and 1.0.0 kept their numbers.
- Allocate as design D3 says, one `gh issue edit <n>... -R troupe-run/<repo> --milestone <title>` per target milestone
  (`--remove-milestone` for none). Then compare every issue in each repository with #119's tables
  (`gh issue list -R troupe-run/<repo> --state all --limit 500 --json number,state,milestone`), and fix or report any
  difference.
- Check `troupe-run/.github`'s `CONTRIBUTING.md` on GitHub shows the Milestones section and its two links work.
- Check text sorting on the board's Milestone grouping and the issues page's milestone filter (design D5). Report what
  you find on troupe-run/troupe#139.
- Check #119 is closed and put it in 0.1.0; check its card on the troupe roadmap board says Done, and fix either if
  not.
- Comment on #119 with the pull request, the archived change, the allocation result and the sorting finding. Check the
  next `drift (out of band)` job passes.
