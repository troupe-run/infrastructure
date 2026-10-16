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

### Requirement: Unsetting the website's Pages settings doesn't disable it
Removing the `pages` setting from the website's declaration SHALL fail the plan rather than disable the site. Deleting
the Pages resource's block or the website's whole declaration removes this guard with it, so such a plan shows the
site being destroyed, and the owner's review of the plan is what stops it.

#### Scenario: Removing the pages setting doesn't take the site down
- **WHEN** the `pages` setting is removed from the website's declaration and a plan runs
- **THEN** the plan refuses to destroy the site, and https://troupe.run keeps serving

#### Scenario: Stopping management leaves the site serving
- **WHEN** the `pages` setting and the Pages resource's block are removed, and a `removed` block that doesn't destroy
  it takes their place
- **THEN** the plan shows the site forgotten, with nothing destroyed, and https://troupe.run keeps serving
