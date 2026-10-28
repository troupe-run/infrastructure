## MODIFIED Requirements

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

### Requirement: Unused features are off
Every managed repository SHALL have its wiki turned off. Classic projects SHALL be turned off on every managed
repository, unless turning them off would hide or unlink the org's project from a repository linked to it. Such a
repository SHALL keep them on, and its declaration SHALL say why. Discussions SHALL be on in `troupe` only. Issues and
Actions SHALL be off in `.github`, and on in every other managed repository. Where a repository's setting differs
from the rest, its declaration SHALL say why.

#### Scenario: No repository has a wiki
- **WHEN** the managed repositories' settings are read from GitHub
- **THEN** none has its wiki turned on

#### Scenario: The org's roadmap stays linked
- **WHEN** the managed repositories' settings have been applied
- **THEN** the org's project is still linked to `troupe`, `infrastructure` and `website`, each has projects on, and
  the project still holds every item it held before

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

## ADDED Requirements

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
