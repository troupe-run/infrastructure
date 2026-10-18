# Proposal

## Why

troupe-run/website's weekly external link check (`.github/workflows/links-weekly.yml`, from troupe-run/website#5)
opens or updates a "Broken external links" issue with the job's `GITHUB_TOKEN`. That token can't write to an org
project, so the issue lands off the troupe roadmap board (project 1), and someone has to add it by hand. Every other
issue in the org goes on the board when it's opened (#59).

## What Changes

- Give website's weekly check a credential that can add an issue to the board. It's an App installation token, minted
  in the run from the App's private key. The owner chose a new, narrow App, `troupe-run-board`, with "Projects: read
  and write" on the organisation and nothing else that can write (design D1, 2026-10-18).
- Declare a `board` environment on troupe-run/website that only `main` may use and no admin can bypass. The App's key
  is held only as that environment's secret. The owner sets the secret from 1Password with a documented command that
  prints nothing. OpenTofu never holds or sets it.
- Declare the App's client ID as a repository variable on website, so the workflow names the App without a secret.
- Record the App's installation in `oob/app-installations.json` and `oob/README.md` so the drift check notices if it
  gains a permission or a repository. Add the `board` environment to the main-only test
  (`scripts/tests/test_main_only_environments.py`).
- Document the owner's manual steps: creating the App, installing it, storing its key, setting the secret and
  rotating the key. GitHub has no API for creating an App.
- **Not in this change:** the edit to website's workflow that mints the token and runs
  `gh project item-add 1 --owner troupe-run --url <issue>`. That's a follow-up change in troupe-run/website, through
  its own pull request, once this change is applied.

## Capabilities

### New Capabilities
- `board-credentials`: the credential an automated run uses to put an issue it opened on the troupe roadmap board.
  That covers the App's installation and permissions, the main-only environment that holds its key, and the variable
  that names the App.

### Modified Capabilities
<!-- None. teams-and-access's drift check already covers every row in oob/app-installations.json; this adds a row,
     not a requirement. -->

## Impact

- `tofu/`: a new `board.tf` with website's `board` environment, its main-only deployment policy and the
  `BOARD_APP_CLIENT_ID` variable.
- `oob/app-installations.json` and `oob/README.md`: the new App's row and its setup steps.
- `scripts/tests/test_main_only_environments.py`: `board` joins `MAIN_ONLY`, and `tofu/board.tf` joins the files it
  reads.
- The infrastructure App needs no new permission. It already writes environments and variables on website.
- GitHub, by hand (owner): create the App, install it, generate and store its key, and set the secret after the apply.
- troupe-run/website: a follow-up change to use the token.
