# Spec Delta

## ADDED Requirements

### Requirement: The website's Pages settings are declared
The `website` repository's GitHub Pages site SHALL be declared here: its custom domain `troupe.run`, HTTPS enforced,
and deploys from GitHub Actions. A difference from GitHub in any of these SHALL appear in the plan.

#### Scenario: Adopting the site changes nothing on GitHub
- **WHEN** the first plan with the declaration runs against the live site
- **THEN** it imports the site, and plans no change to it and no change to any other repository

#### Scenario: A custom domain changed by hand shows as drift
- **WHEN** an owner removes or changes the website's custom domain on GitHub
- **THEN** the next plan shows it changing back to `troupe.run`

#### Scenario: HTTPS turned off by hand shows as drift
- **WHEN** an owner turns off "Enforce HTTPS" for the website on GitHub
- **THEN** the next plan shows it changing back to enforced

#### Scenario: Deploying from a branch shows as drift
- **WHEN** an owner switches the website's Pages source from GitHub Actions to a branch
- **THEN** the next plan shows it changing back to GitHub Actions

### Requirement: An apply never disables the website
No plan or apply SHALL disable the website's Pages site. Removing the site's declaration SHALL leave the site serving
on GitHub as it is.

#### Scenario: Removing the declaration doesn't take the site down
- **WHEN** the site's declaration is removed and a plan runs
- **THEN** the plan refuses to destroy it, and https://troupe.run keeps serving
