## MODIFIED Requirements

### Requirement: The website deploys from main only
The `website` repository SHALL have an environment named `github-pages`, the one its deploy job uses, whose
deployment branches are limited to `main` and which no admin can bypass. The environment and its branch policy SHALL
be declared in this repository, so a difference on GitHub shows in the next plan.

#### Scenario: A run on another branch asks to deploy
- **WHEN** a workflow run on a branch other than `main` uses the `github-pages` environment
- **THEN** GitHub refuses the deployment, and nothing from that run reaches troupe.run

#### Scenario: The branch policy is changed by hand
- **WHEN** someone removes or widens the `github-pages` environment's deployment branches, or allows admins to bypass
  them, on GitHub
- **THEN** the next plan shows the change being reverted

#### Scenario: main still deploys
- **WHEN** a push to the website's `main` passes CI after the declaration has been applied
- **THEN** the deploy job's deployment to `github-pages` succeeds, and https://troupe.run serves that commit

#### Scenario: Removing or weakening the declaration fails the check
- **WHEN** a change deletes the `github-pages` environment's declaration, lets it deploy from a branch other than
  `main`, or lets admins bypass it
- **THEN** `scripts/check.py` fails, naming the environment and what changed, before any plan is made
