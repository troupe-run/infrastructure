# Proposal

## Why

teams-and-access's requirement "No App is installed that nothing uses" is out of date. Its scenario "The declared
installations are only the ones in use" says the drift check finds exactly DCO, `troupe-run-infrastructure` and
`troupe-run-release`. The org now has a fourth App, `troupe-run-board`, which #59 (`add-link-issue-to-board`) created
and declared in `oob/app-installations.json`. #59 didn't touch this spec, and #62 (`run-oob-check-daily`) added the
App only to the requirement above it. So the scenario contradicts the drift check, which finds four Apps and reports
no difference. The requirement also says every App is used by something this repository declares or documents, but
only the release App has a scenario saying what that is (#97).

## What Changes

- The scenario "The declared installations are only the ones in use" lists all four Apps: DCO,
  `troupe-run-infrastructure`, `troupe-run-release` and `troupe-run-board`.
- A new scenario, "The board App is used", names what uses `troupe-run-board`, from what board-credentials,
  `tofu/board.tf` and `oob/README.md` say:
  - website's weekly link check, which adds its issue to the board;
  - the `board` environment and the `BOARD_APP_CLIENT_ID` variable this repository declares for it on website;
  - the `BOARD_APP_PRIVATE_KEY` secret, which `oob/README.md` documents setting.
- The rest of the requirement, including the release App's scenario, is copied unchanged into the delta.

Out of scope: website's job that uses the App's token is troupe-run/website#18. The new scenario names the link check
as the App's user, the way the release App's scenario names troupe's release workflow, so it stays true when #18
lands and needs no change then.

A grep of `openspec/specs/` for the org's Apps found no other list that #59 missed. Line 11 of teams-and-access
already names all four. `oob/README.md`'s table has `troupe-run-board`. release-credentials, board-credentials and
state-and-apply each name only their own App.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `teams-and-access`: "No App is installed that nothing uses" lists the four Apps, and says what uses the board App.

## Impact

- `openspec/specs/teams-and-access/spec.md` only, at archive.
- No change to any resource, script or workflow. The pull request touches only `openspec/`, so it needs no plan.
- The drift check (`scripts/oob.py`) is unchanged. It already declares the four installations and should report no
  difference.
