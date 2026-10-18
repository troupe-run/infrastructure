## MODIFIED Requirements

### Requirement: The release key is readable from main only
troupe SHALL have an environment named `release` whose deployment branches are limited to `main`, and which no
admin can bypass. The App's private key SHALL be held only as that environment's secret `RELEASE_APP_PRIVATE_KEY`, so
a workflow run on any other branch can't read it.

#### Scenario: A run on another branch asks for the environment
- **WHEN** a workflow run on a branch other than `main` uses the `release` environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from it

#### Scenario: The branch policy is changed by hand
- **WHEN** someone widens the `release` environment's deployment branches, or allows admins to bypass them, on GitHub
- **THEN** the next plan shows the change being reverted

#### Scenario: Removing or weakening the declaration fails the check
- **WHEN** a change deletes the `release` environment's declaration, lets it deploy from a branch other than `main`,
  or lets admins bypass it
- **THEN** `scripts/check.py` fails, naming the environment and what changed, before any plan is made
