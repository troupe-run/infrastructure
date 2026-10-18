## MODIFIED Requirements

### Requirement: No App is installed that nothing uses
Each App installed in the org SHALL be used by something this repository declares or documents. An App that nothing
uses SHALL be deleted, and its declaration and its keys removed with it.

#### Scenario: The declared installations are only the ones in use
- **WHEN** the drift check reads the org's App installations
- **THEN** it finds exactly DCO, `troupe-run-infrastructure`, `troupe-run-release` and `troupe-run-board`, and reports
  no difference

#### Scenario: The release App is used
- **WHEN** someone asks what uses `troupe-run-release`
- **THEN** this repository names troupe's release workflow (troupe-run/troupe#23) and the `release` environment and
  variable it declares for it (spec: release-credentials)

#### Scenario: The board App is used
- **WHEN** someone asks what uses `troupe-run-board`
- **THEN** this repository names website's weekly link check, which adds its "Broken external links" issue to the
  troupe roadmap board, the `board` environment and `BOARD_APP_CLIENT_ID` variable it declares for it on website, and
  the `BOARD_APP_PRIVATE_KEY` secret it documents (spec: board-credentials)
