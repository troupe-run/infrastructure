# Proposal

## Why

GitHub turns off a public repository's scheduled workflows after 60 days with no activity in it. troupe-run/website's
weekly external link check (`links-weekly.yml`) fails its run and opens an issue when a link breaks, but once its
schedule is off nothing runs, so nothing fails and no issue opens (#60). A watcher inside website would be turned off
with the check it watches, so the watcher lives here.

## What Changes

- A new scheduled workflow in this repository, `.github/workflows/schedules.yml`, runs daily. For each watched
  workflow it asks the Actions API for the workflow's `state` and its latest run started by the schedule. It finds a
  problem when the state isn't `active`, when the latest scheduled run is older than the workflow's declared limit
  (8 days for website's weekly check), when it has never run on its schedule, or when the workflow isn't found.
- One tracking issue in troupe-run/infrastructure, "Scheduled workflows stopped running": opened when a problem is
  found, commented on only when the problems change, and closed by the first clean run. It's the same open, comment
  and close pattern website's check uses. The issue names each problem and its fix (for example
  `gh workflow enable links-weekly.yml -R troupe-run/website`). A run that finds a problem fails, so the run history
  shows it too.
- A run that can't read a watched workflow (an error other than "not found") fails without touching the issue: it
  can't tell whether the check is running, so it says neither.
- **Generalised:** the watched workflows are declared as data, in one file (`scripts/watched-schedules.json`), each
  with its repository, workflow file and age limit. Today it lists one, website's `links-weekly.yml`. Another
  scheduled workflow is watched by adding a line (design D2).
- The issue goes on the troupe roadmap board. The watcher opens it with `GITHUB_TOKEN`, which can't write an org
  project, so a separate job adds it with the existing `troupe-run-board` App's token, as website's check does. That
  needs a `board` environment on infrastructure, main-only with no admin bypass, holding the App's key, and the
  `BOARD_APP_CLIENT_ID` variable there. The owner sets the secret from 1Password after the apply.
- A run started by hand can name one extra workflow to watch, so the issue path, board included, can be proved
  against a throwaway repository without stopping website's check.
- **Not in this change:**
  - Turning a stopped workflow back on automatically. It needs an Actions write permission on website that no
    credential here holds, and enabling a workflow by hand is one command the issue gives.
  - Watching infrastructure's own `tofu.yml`. If this repository goes 60 days without activity, the watcher stops
    with it, so it can't catch that. Its daily state commits keep it active today. Having website's check watch
    infrastructure back would close the gap; that's a website change, to raise as its own issue.

## Capabilities

### New Capabilities
- `schedule-watch`: noticing when a watched scheduled workflow in the org stops running, and the tracking issue that
  reports it.

### Modified Capabilities
- `board-credentials`: the `board` environment and the `BOARD_APP_CLIENT_ID` variable are declared on infrastructure
  as well as website, with the same main-only rule.

## Impact

- `.github/workflows/schedules.yml` (new) and `scripts/watch_schedules.py` (new, standard library, reads with `gh`),
  with `scripts/watched-schedules.json` and tests under `scripts/tests/`.
- `tofu/board.tf`: the `board` environment, its main-only policy and the variable on infrastructure too.
- `scripts/tests/test_main_only_environments.py`: `MAIN_ONLY` is keyed by repository and environment, since `board`
  is now in two repositories.
- `README.md` and `oob/README.md`: the watcher, and the owner's step to set `BOARD_APP_PRIVATE_KEY` on
  infrastructure's `board` environment.
- No new App permission. The infrastructure App already writes environments and variables here; the board App
  already adds public issues from any org repository without being installed on it.
- GitHub, by hand (owner): approve the plan, set the secret, and look over the first real issue on the board.
