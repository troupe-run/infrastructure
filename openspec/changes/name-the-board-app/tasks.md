# Tasks

## 1. The delta (spec: teams-and-access)

- [ ] 1.1 Check the delta's "No App is installed that nothing uses" against the main spec. Verify with `diff` that
      the requirement text and "The release App is used" are copied unchanged, that the only differences are the
      fourth App in "The declared installations are only the ones in use" and the new scenario "The board App is
      used", and that `openspec validate name-the-board-app --strict` passes
- [ ] 1.2 Check each thing "The board App is used" names against its source. Verify that `tofu/board.tf` declares
      the `board` environment and `BOARD_APP_CLIENT_ID` on website, that `oob/README.md` documents setting
      `BOARD_APP_PRIVATE_KEY`, that board-credentials specifies all three, and that the scenario says nothing that
      troupe-run/website#18 (the job that uses them) will make untrue

## 2. The live org

- [ ] 2.1 Run `uv run scripts/oob.py`. Verify it reports no difference, and that its App installations check covers
      the four Apps the scenario lists, no more and no fewer (`oob/app-installations.json`)
- [ ] 2.2 Grep `openspec/specs/`, `README.md`, `oob/README.md` and `docs/` again for lists of the org's Apps. Verify
      none still leaves out `troupe-run-board`, or record any that does for the owner
- [ ] 2.3 Verify `uv run scripts/check.py` passes, and that `scripts/plan_needed.py` prints `plan=false` for the
      branch's changed paths (`git diff --name-only origin/main...HEAD`)

## Workflow follow-up

- Commit as Conventional Commits, signed off, saying why.
- Open the PR with `Closes #97`, using `--body-file` with a literal path, and quoting 1.1's diff, 2.1's output and
  2.3's `plan=false` as evidence. The plan job should be skipped.
- Archive on the branch before the owner merges by rebase (`/opsx:archive`).
- After the merge, comment on #97 with the PR and the archived change, check it's closed and its card says Done, and
  remove the branch and worktree.
