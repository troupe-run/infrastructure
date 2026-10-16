# Proposal

## Why

The guard's git hooks reach `troupe-run/website` as `100644`, so git skips all three of them and nothing checks a
commit or a push there locally (#69). `github_repository_file` can't set a file mode, so every file it creates is
non-executable, and nothing reports the gap. `troupe` escaped only because its hooks were committed by hand as
`100755` before they were imported. Any repository added to the guard's targets later will be missing its hooks
the same way.

## What Changes

- A delivered file SHALL have its source's file mode in every governed repository, as well as its content. Today
  that means the three `.githooks/*` files are `100755`; every other delivered file is `100644`, as its source is.
- The plan of `main` (and a pull request's plan) checks each delivered file's mode in each target. It shows a
  difference as a pending change, so the run waits for the owner's approval just as it does for a content change. The
  daily plan finds a mode that has drifted within a day.
- After the approved apply, CI sets each listed file's mode as the infrastructure App, in one Git Data API commit per
  repository whose message is a Conventional Commit naming the files. It makes no commit when every mode already
  matches. The first apply after this change merges sets `website`'s hooks to `100755`.
- When a hook isn't executable in a clone, starting a Claude Code session or running the check says that git will
  skip it, and where the fix is. Activation no longer reports success in silence while the hooks can't run.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `guard-delivery`: a new requirement that a delivered file has its source's mode, planned and applied like its
  content, and restored after drift.
- `development-workflow`: making the git hooks active also says when a hook can't run because it isn't executable.

## Impact

- `scripts/`: a new script that reads targets' file modes from a saved plan and GitHub, and sets them as the App
  (standard library only, like `commit_state.py`). It has tests.
- `scripts/guard.py` (`activate_hooks` and its callers) and its tests. Because the guard is delivered, this change
  goes out to `troupe` and `website` through a delivery.
- `.github/workflows/tofu.yml`: the plan jobs run the mode check and count its differences as changes. The apply job
  runs the mode fix after `tofu apply`, with an App token scoped to the repositories it changes.
- `website`'s `main` gains one App commit that sets its three hooks to `100755`. `troupe` is unchanged; its modes
  already match.
- Docs: `docs/development-workflow.md` and the README's apply and break-glass sections. A local break-glass apply
  doesn't set modes, so the README says to let the next CI plan do it.
