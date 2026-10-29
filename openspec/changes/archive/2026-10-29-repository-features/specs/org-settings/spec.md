## ADDED Requirements

### Requirement: Members can't create Pages sites
The org's settings SHALL NOT let members create GitHub Pages sites, public or private. The website's site, which the
`website` repository's declaration manages, SHALL keep serving and deploying. A difference from GitHub SHALL appear in
the plan.

#### Scenario: Pages creation turned back on by hand shows as drift
- **WHEN** an owner lets members create public or private Pages sites on GitHub
- **THEN** the next plan shows the setting changing back to off

#### Scenario: The website keeps deploying
- **WHEN** the setting is applied, and the website's deploy job next runs on `main`
- **THEN** its deployment to `github-pages` succeeds, and https://troupe.run serves that commit
