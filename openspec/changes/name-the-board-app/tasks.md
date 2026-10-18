# Tasks

## 1. The delta (spec: teams-and-access)

- [x] 1.1 Check the delta's "No App is installed that nothing uses" against the main spec. Verify with `diff` that
      the requirement text and "The release App is used" are copied unchanged, that the only differences are the
      fourth App in "The declared installations are only the ones in use" and the new scenario "The board App is
      used", and that `openspec validate name-the-board-app --strict` passes
      Done 2026-10-18: `diff` of main spec lines 42-53 against the delta shows only the fourth App (line 7) and the
      added scenario (lines 14-19). `Change 'name-the-board-app' is valid`
- [x] 1.2 Check each thing "The board App is used" names against its source. Verify that `tofu/board.tf` declares
      the `board` environment and `BOARD_APP_CLIENT_ID` on website, that `oob/README.md` documents setting
      `BOARD_APP_PRIVATE_KEY`, that board-credentials specifies all three, and that the scenario says nothing that
      troupe-run/website#18 (the job that uses them) will make untrue
      Done 2026-10-18: `tofu/board.tf:17-18` (`board` on `module.repo_website`), `:36-37` (`BOARD_APP_CLIENT_ID`);
      `oob/README.md:133` (`gh secret set BOARD_APP_PRIVATE_KEY --env board`); board-credentials specifies all three.
      website's `links-weekly.yml` is the weekly check that opens "Broken external links". "Which adds its issue to
      the board" describes it once #18 lands; owner chose wording that #18 won't have to undo (2026-10-18)

## 2. The live org

- [x] 2.1 Run `uv run scripts/oob.py`. Verify it reports no difference, and that its App installations check covers
      the four Apps the scenario lists, no more and no fewer (`oob/app-installations.json`)
      Done 2026-10-18: `oob: no differences (.github files, org settings, App installations, issue types, projects,
      troupe specs, troupe label descriptions, code security, milestones)`, exit 0. The declaration's `app_slug`s are
      `dco`, `troupe-run-board`, `troupe-run-infrastructure` and `troupe-run-release`, and the check reports both
      missing and undeclared installations (`differences()` in `scripts/oob.py`)
- [x] 2.2 Grep `openspec/specs/`, `README.md`, `oob/README.md` and `docs/` again for lists of the org's Apps. Verify
      none still leaves out `troupe-run-board`, or record any that does for the owner
      Done 2026-10-18: the only list without it is teams-and-access line 48, which this change fixes. Line 11 and
      `oob/README.md`'s installation table name all four; README.md and the other specs name only one App each
- [x] 2.3 Verify `uv run scripts/check.py` passes, and that `scripts/plan_needed.py` prints `plan=false` for the
      branch's changed paths (`git diff --name-only origin/main...HEAD`)
      Done 2026-10-18: `check: all gates passed`; the four changed paths are all under
      `openspec/changes/name-the-board-app/`, and `plan_needed.py` prints `plan=false`

## Workflow follow-up

- Commit as Conventional Commits, signed off, saying why.
- Open the PR with `Closes #97`, using `--body-file` with a literal path, and quoting 1.1's diff, 2.1's output and
  2.3's `plan=false` as evidence. The plan job should be skipped.
- Archive on the branch before the owner merges by rebase (`/opsx:archive`).
- After the merge, comment on #97 with the PR and the archived change, check it's closed and its card says Done, and
  remove the branch and worktree.
