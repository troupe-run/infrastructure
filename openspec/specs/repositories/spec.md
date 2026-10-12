# repositories Specification

## Purpose

Says which of the org's repositories this repo manages and holds their settings, so a repository's configuration is
declared once, drift is visible, and no apply can delete a repository.

## Requirements

### Requirement: The org's active repositories are managed
Every repository in the org that isn't archived SHALL be declared here: today `troupe`, `.github`, `infrastructure`
and `website`. Archived repositories SHALL NOT be managed.

#### Scenario: Active repositories are declared
- **WHEN** the declared repositories are compared with the org's repositories that aren't archived
- **THEN** the two lists are the same

#### Scenario: Archived repositories are left alone
- **WHEN** a plan runs
- **THEN** it reads or changes nothing in an archived repository

#### Scenario: The website keeps serving under its new name
- **WHEN** the website repository has been renamed from `troupe-run.github.io` to `website`
- **THEN** its Pages site still has the custom domain `troupe.run` with HTTPS enforced, and https://troupe.run serves
  the site

### Requirement: A repository's settings are declared
Each managed repository's settings SHALL be declared, including its visibility, its allowed merge methods, whether
branches are deleted on merge, and its wiki, issues, projects and discussions. A difference from GitHub SHALL appear
in the plan.

#### Scenario: A merge setting changed by hand shows as drift
- **WHEN** an owner changes a managed repository's allowed merge methods on GitHub
- **THEN** the next plan shows them changing back to the declared values

### Requirement: An apply never deletes a repository
No plan or apply SHALL delete or archive a managed repository. Removing a repository from this repo's management
SHALL leave the repository itself unchanged on GitHub.

#### Scenario: Removing a declaration doesn't delete the repository
- **WHEN** a repository's declaration is removed and a plan runs
- **THEN** the plan refuses to destroy it, and the repository stays on GitHub as it is
