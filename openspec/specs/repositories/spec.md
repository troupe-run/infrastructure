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
- **THEN** the org's project is still linked to `troupe` and `website`, and still holds every item it held before

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

### Requirement: Repositories have their security features on
Every managed repository SHALL have the dependency graph, Dependabot alerts, Dependabot security updates, secret
scanning and secret scanning push protection turned on. Each SHALL be declared, so that one turned off on GitHub
appears in the plan, or in the drift check for what OpenTofu can't manage. Turning them on SHALL change no other
setting of the repository.

#### Scenario: Every repository reads as protected
- **WHEN** each managed repository's security settings are read from GitHub after an apply
- **THEN** the dependency graph, Dependabot alerts, Dependabot security updates, secret scanning and push protection
  are all on, and neither the plan nor the drift check shows a difference

#### Scenario: A feature turned off by hand shows as drift
- **WHEN** an owner turns off any of the five features on a managed repository on GitHub
- **THEN** the next plan shows it turning back on, or the drift check reports it and exits non-zero

#### Scenario: Dependabot can see the dependencies
- **WHEN** a managed repository's dependency graph is read from GitHub
- **THEN** it lists the repository's packages, so Dependabot can raise an alert for a vulnerable one

#### Scenario: Turning them on leaves the other settings alone
- **WHEN** the features are turned on for a repository whose other settings already match the declaration
- **THEN** its other settings on GitHub are the same afterwards, the homepage and description included

### Requirement: Push protection lets the org's own commits through
Push protection SHALL NOT refuse the commits this repository's automation makes: the App's commits of the encrypted
state, and its deliveries of the guard's files. It SHALL still refuse a commit that contains a token GitHub
recognises.

#### Scenario: The state commit is accepted
- **WHEN** the encrypted state is committed to a repository that has push protection on
- **THEN** the commit is accepted

#### Scenario: A guard delivery is accepted
- **WHEN** the guard's delivered files are committed through the API to a repository that has push protection on
- **THEN** the commit is accepted

#### Scenario: A token is refused
- **WHEN** a commit containing a string in a token format GitHub scans for is pushed to a repository that has push
  protection on
- **THEN** the push is refused
