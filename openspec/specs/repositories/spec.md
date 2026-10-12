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

### Requirement: Repositories allow only rebase merges
Every managed repository SHALL allow pull requests to be merged by rebase only. Merge commits and squash merges SHALL
be turned off in its settings, so the settings agree with the ruleset and GitHub offers no merge button the ruleset
would refuse.

#### Scenario: Only rebase is offered
- **WHEN** a managed repository's settings are read from GitHub
- **THEN** rebase merging is allowed, merge commits and squash merging are not, and the plan shows no difference

### Requirement: Branches are deleted on merge
Every managed repository SHALL delete a pull request's branch when the pull request is merged.

#### Scenario: A merged branch is gone
- **WHEN** a pull request in a managed repository is merged
- **THEN** its head branch no longer exists on GitHub

### Requirement: Unused features are off
Every managed repository SHALL have its wiki turned off. Classic projects SHALL be turned off on every managed
repository, unless turning them off would hide or unlink the org's project from a repository linked to it. Such a
repository SHALL keep them on, and its declaration SHALL say why.

#### Scenario: No repository has a wiki
- **WHEN** the managed repositories' settings are read from GitHub
- **THEN** none has its wiki turned on

#### Scenario: The org's roadmap stays linked
- **WHEN** the managed repositories' settings have been applied
- **THEN** the org's project is still linked to `troupe`, and still holds every item it held before
