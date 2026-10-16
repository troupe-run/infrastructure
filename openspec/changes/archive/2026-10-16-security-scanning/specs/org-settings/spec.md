## ADDED Requirements

### Requirement: New repositories start with their security features on
The org's defaults SHALL turn on Dependabot alerts, Dependabot security updates, the dependency graph, secret
scanning and push protection for each repository created in the org. The defaults SHALL be declared, so a difference
from GitHub is visible. Whether they take effect SHALL be shown on a repository created after they're applied, not
read only from the org's settings.

#### Scenario: A new repository is protected from the start
- **WHEN** a public repository is created in the org after the defaults are applied
- **THEN** it has Dependabot alerts, Dependabot security updates, secret scanning and push protection on, without
  anything being applied to it

#### Scenario: A default turned off by hand is visible
- **WHEN** an owner turns off one of these defaults on GitHub
- **THEN** the next plan, or the drift check for what OpenTofu can't manage, reports the difference
