# Spec Delta

## ADDED Requirements

### Requirement: A change to the milestones rebuilds troupe.run
A push to `main` that changes `tofu/milestones.json` SHALL dispatch troupe-run/website's `deploy.yml` on `main`, with
no inputs, so `/status/` shows the new release list once that deploy finishes. A push to `main` that doesn't change
the file, and any push to another branch, SHALL dispatch nothing. The sending job SHALL check out nothing, hold no
`GITHUB_TOKEN` permission, and use only the docs App's token (spec: docs-build-credentials).

#### Scenario: A milestone is re-described
- **WHEN** a pull request that changes a description in `tofu/milestones.json` merges to `main`
- **THEN** a website Deploy run starts on `main`, triggered by `workflow_dispatch`

#### Scenario: A push that doesn't touch the milestones
- **WHEN** a push to `main` changes other files only, such as the state commit after an apply
- **THEN** no website Deploy run is dispatched

#### Scenario: A branch that changes the milestones
- **WHEN** a push to a branch other than `main`, or a pull request, changes `tofu/milestones.json`
- **THEN** no website Deploy run is dispatched

#### Scenario: The notice is weakened
- **WHEN** a change makes the workflow run on another event or branch, gives its job a `GITHUB_TOKEN` permission or a
  checkout, drops its `docs` environment, widens the token it mints, or dispatches with inputs
- **THEN** `scripts/check.py` fails, naming what changed
