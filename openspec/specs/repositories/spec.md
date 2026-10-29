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
branches are deleted on merge, and its wiki, issues, projects, discussions and Actions. A difference from GitHub SHALL
appear in the plan.

#### Scenario: A merge setting changed by hand shows as drift
- **WHEN** an owner changes a managed repository's allowed merge methods on GitHub
- **THEN** the next plan shows them changing back to the declared values

#### Scenario: Actions turned on by hand shows as drift
- **WHEN** an owner turns Actions on in a managed repository whose declaration has it off
- **THEN** the next plan shows Actions turning back off

### Requirement: An apply never deletes a repository
No plan or apply SHALL delete a managed repository. Taking a repository out of this repo's management SHALL leave
it unchanged on GitHub. A plan that would destroy a repository SHALL be refused while its declaration is still
there. If its declaration is deleted, the plan SHALL show the repository being destroyed, and an approved apply SHALL
archive it rather than delete it.

#### Scenario: Taking a repository out of management leaves it as it is
- **WHEN** a repository's declaration is replaced by a `removed` block that doesn't destroy it, and a plan runs
- **THEN** the plan forgets the repository and destroys nothing, and the repository stays on GitHub as it is

#### Scenario: A destroy the declaration still names is refused
- **WHEN** the declaration is still there but would destroy the repository (it's switched off, or a change forces a
  replacement), and a plan runs
- **THEN** the plan fails, naming the repository, and nothing is applied

#### Scenario: Removing a declaration doesn't delete the repository
- **WHEN** a repository's declaration is deleted outright and a plan runs
- **THEN** the plan shows the repository being destroyed, so the owner can refuse it before approving the apply
- **AND** if the apply is approved, the repository is archived on GitHub, not deleted

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
- **THEN** the org's project is still linked to `troupe`, `infrastructure` and `website`, each has projects on, and
  the project still holds every item it held before

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

### Requirement: Auto-merge is on exactly where the merge queue is
A managed repository SHALL allow auto-merge when its merge queue is on, and SHALL NOT otherwise. With the queue on, a
merge from the command line (`gh pr merge`) then adds the pull request to the queue, so the owner's bypass, which
skips the queue, is never the only way to merge from a terminal.

#### Scenario: A repository with its queue on
- **WHEN** a repository whose merge queue is on has its settings read from GitHub
- **THEN** auto-merge is allowed, and the plan shows no difference

#### Scenario: Merging from the command line queues the pull request
- **WHEN** the owner runs `gh pr merge <n>` on a pull request in a repository whose queue is on
- **THEN** the pull request joins the merge queue, and lands only once the queue's checks pass

#### Scenario: A repository with its queue off
- **WHEN** a repository whose merge queue is off has its settings read from GitHub
- **THEN** auto-merge isn't allowed

### Requirement: Discussions, issues and Actions are on only where they're used
Discussions SHALL be on in `troupe` only. Issues and Actions SHALL be off in `.github`, and on in every other managed
repository. Where a repository's setting differs from the rest, its declaration SHALL say why.

#### Scenario: Only troupe has discussions
- **WHEN** the managed repositories' settings are read from GitHub
- **THEN** `troupe` has discussions on, and `.github`, `infrastructure` and `website` have them off

#### Scenario: Nothing can be filed in .github
- **WHEN** someone opens `.github`'s issues on GitHub
- **THEN** issues are turned off there, and no new issue can be opened

#### Scenario: The org's issue forms still reach the other repositories
- **WHEN** issues are off in `.github`, and someone opens a new issue in `infrastructure`, which has no forms of its
  own
- **THEN** GitHub offers the org's Feature, Bug and Decision forms from `.github`

#### Scenario: No workflow runs in .github
- **WHEN** `.github`'s Actions settings are read from GitHub
- **THEN** Actions is turned off, so a workflow file added there would never run

### Requirement: Private vulnerability reporting is on everywhere
Every managed repository SHALL have private vulnerability reporting turned on, so the org's security policy, which
asks for reports through it, works in each. OpenTofu can't manage it, so the drift check for what OpenTofu can't
manage SHALL report a repository that has it off. A repository whose setting can't be read SHALL be an error, never
"off" or "on".

#### Scenario: Every repository takes private reports
- **WHEN** each managed repository's private vulnerability reporting is read from GitHub after the change
- **THEN** it is on in all four, and the drift check reports no difference

#### Scenario: Reporting turned off by hand is reported
- **WHEN** an owner turns private vulnerability reporting off in a managed repository
- **THEN** the drift check reports that repository and exits non-zero, and GitHub is unchanged

#### Scenario: A refused read is an error
- **WHEN** GitHub refuses the read of a repository's private vulnerability reporting
- **THEN** the drift check exits non-zero with an error naming the repository and saying its state is unknown

### Requirement: Pull requests are off in .github only
`.github` SHALL have pull requests turned off, since only the App changes its `main` and its files are written from
this repository. Every other managed repository SHALL have them on. OpenTofu can't manage the setting, so the drift
check for what OpenTofu can't manage SHALL report a repository whose setting differs. A read GitHub refuses SHALL be
an error naming the repository.

#### Scenario: Nothing can be proposed in .github
- **WHEN** someone opens `.github` on GitHub
- **THEN** pull requests are turned off there, and none can be opened

#### Scenario: The App still writes .github
- **WHEN** the App delivers a changed file to `.github` after pull requests are off
- **THEN** its commit lands on `main`

#### Scenario: Pull requests turned on by hand are reported
- **WHEN** an owner turns pull requests on in `.github`, or off in another managed repository
- **THEN** the drift check reports that repository and exits non-zero, and GitHub is unchanged

### Requirement: Sponsorships is off everywhere
Every managed repository SHALL have Sponsorships (the Sponsor button) turned off. OpenTofu can't manage it, so the
drift check for what OpenTofu can't manage SHALL report a repository that has it on. A read GitHub refuses SHALL be an
error naming the repository.

#### Scenario: Sponsorships turned on by hand is reported
- **WHEN** an owner turns Sponsorships on in a managed repository
- **THEN** the drift check reports that repository and exits non-zero, and GitHub is unchanged

### Requirement: troupe's discussion categories are declared
`troupe`'s discussion categories SHALL be declared: Q&A, Ideas and Announcements, each with its slug and whether it
takes answers (only Q&A does). OpenTofu can't manage them, so the drift check for what OpenTofu can't manage SHALL
report a category added, removed or changed on GitHub. A read GitHub refuses SHALL be an error.

#### Scenario: The declared categories match
- **WHEN** `troupe`'s discussion categories on GitHub are the declared three, with their slugs and answer settings
- **THEN** the drift check reports no difference for them

#### Scenario: A category added by hand is reported
- **WHEN** a discussion category exists in `troupe` that the declaration doesn't list
- **THEN** the drift check reports it by name and exits non-zero, and GitHub is unchanged

#### Scenario: Discussions turned off are reported
- **WHEN** discussions are turned off in `troupe`, so it has no categories
- **THEN** the drift check reports each declared category as missing and exits non-zero
