# org-settings Specification

## Purpose

Declares the troupe-run organisation's own configuration (its settings, its issue types and its project) in this
repo, so that any difference from GitHub is visible and changes go through pull requests.

## Requirements

### Requirement: The org's settings are declared
The organisation's settings SHALL be declared in this repository, including two-factor enforcement, web commit
sign-off, who may create repositories and the default repository permission. A difference between the declaration
and GitHub SHALL appear in the plan.

#### Scenario: A setting changed by hand shows as drift
- **WHEN** an owner changes a declared org setting on GitHub's website
- **THEN** the next plan shows that setting changing back to its declared value

### Requirement: Issue types and the org project are checked for drift
The org's issue types and its project SHALL be declared in this repository. A check SHALL report any difference
between the declaration and GitHub without changing GitHub. Whatever OpenTofu can't manage SHALL be documented as
outside OpenTofu's control, with the check named as its replacement.

#### Scenario: An issue type added by hand is reported
- **WHEN** an issue type exists on GitHub that the declaration doesn't list
- **THEN** the drift check reports it and exits non-zero, and GitHub is unchanged

#### Scenario: The declared state matches
- **WHEN** GitHub's issue types and project match the declaration
- **THEN** the drift check reports no differences and exits zero

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
