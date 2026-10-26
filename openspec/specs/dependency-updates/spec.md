# dependency-updates Specification

## Purpose
How Dependabot keeps each managed repository's dependencies up to date. One policy is declared in this repository,
and each repository's `.github/dependabot.yml` is generated from it and delivered by the App.

## Requirements

### Requirement: Each repository's Dependabot configuration is generated from one policy
Each managed repository with at least one declared Dependabot ecosystem SHALL get a `.github/dependabot.yml`. It SHALL
be generated from the shared policy and that repository's declared ecosystems, with one update entry per ecosystem.
A repository with no declared ecosystem SHALL get no file. The policy, the ecosystems and their labels SHALL each be
declared in one place.

#### Scenario: Each repository gets its ecosystems
- **WHEN** the generated configurations are read
- **THEN** troupe's has entries for `uv` and `github-actions`, website's for `npm` and `github-actions`, and
  infrastructure's for `uv` and `github-actions`, and each entry's directory is the policy's directory for that
  ecosystem

#### Scenario: A repository with no dependencies
- **WHEN** the generated configurations are read
- **THEN** there is none for `.github`

#### Scenario: An ecosystem with no declared directory
- **WHEN** a repository's declared ecosystems name one that the policy gives no directory
- **THEN** `scripts/check.py` fails, naming the repository and the ecosystem

### Requirement: Version updates run weekly, after a cooldown
Every update entry SHALL run version updates weekly, on the policy's day and time. Each SHALL wait the policy's
cooldown before proposing a release: the policy's patch, minor and major days where the ecosystem supports them, and
its default days otherwise. Each update SHALL be its own pull request, with no grouping, and the open pull request
limit SHALL be Dependabot's default. Security updates SHALL keep running, unaffected by the cooldown.

#### Scenario: The schedule is the same everywhere
- **WHEN** every generated configuration's entries are read
- **THEN** each has a weekly interval with the policy's day, time and timezone, and none has `groups` or
  `open-pull-requests-limit`

#### Scenario: Cooldown by kind of release
- **WHEN** the `npm` and `uv` entries are read
- **THEN** each has the policy's patch, minor and major cooldown days, the major one the longest

#### Scenario: Cooldown where an ecosystem has no release kinds
- **WHEN** a `github-actions` entry is read
- **THEN** it has the policy's default cooldown days and no patch, minor or major days

#### Scenario: A scheduled run opens version updates
- **WHEN** Dependabot's scheduled run finds a newer release of a dependency, older than the cooldown
- **THEN** it opens one pull request for that dependency's update

### Requirement: Dependabot's pull requests are Conventional and carry only declared labels
Each update entry SHALL set the commit prefix `chore` with the dependency scope, so a pull request's title and commit
read `chore(deps): …` or `chore(deps-dev): …`. Each entry SHALL set its labels to `dependencies` and its ecosystem's
declared label, both taken from the declared Dependabot labels. Dependabot's own default labels SHALL NOT be used.

#### Scenario: A version update's title
- **WHEN** Dependabot opens a version update pull request in a managed repository
- **THEN** its title starts with `chore(deps):` or `chore(deps-dev):`

#### Scenario: A version update's labels
- **WHEN** Dependabot opens a pull request from the `github-actions` entry in troupe
- **THEN** its labels are exactly `dependencies` and `github_actions`, both declared in this repository

#### Scenario: Labels follow the declaration
- **WHEN** the generated configurations are read
- **THEN** every label in every entry is the name of a label declared for that repository's Dependabot ecosystems

### Requirement: The App delivers each repository's configuration
The infrastructure App SHALL commit each generated `.github/dependabot.yml` to its repository's `main`, this
repository included, without a pull request, in a Conventional Commit naming the file and its content. A difference
from the generated content SHALL appear in the plan, and an apply SHALL restore it. A plan where nothing changed
SHALL deliver nothing.

#### Scenario: Every repository with ecosystems holds its file
- **WHEN** the managed state is read after an apply
- **THEN** troupe, website and infrastructure each hold `.github/dependabot.yml` with its generated content, and
  `.github` holds none

#### Scenario: A hand edit shows as drift
- **WHEN** someone changes `.github/dependabot.yml` on `main` in any of the three repositories
- **THEN** the next plan shows the file returning to its generated content, and applying it restores that content

#### Scenario: Nothing changed
- **WHEN** a plan runs and neither the policy, the ecosystems nor the labels have changed since the last delivery
- **THEN** the plan shows no change to any `.github/dependabot.yml`

#### Scenario: The file says where it comes from
- **WHEN** someone opens `.github/dependabot.yml` in any of the three repositories
- **THEN** its opening lines say it is generated in `troupe-run/infrastructure` and is changed there

### Requirement: The file is changed only at its source in a repository that receives the guard
In each repository that receives the guard, `.github/dependabot.yml` SHALL be named in the delivered list, so the
delivered-file rule applies to it as to the guard's files.

#### Scenario: Committing a change to it in troupe
- **WHEN** a contributor in troupe commits a change to `.github/dependabot.yml`
- **THEN** the commit is refused, naming the rule and saying to change it in `troupe-run/infrastructure`

#### Scenario: The delivered list names it
- **WHEN** troupe's or website's `.github/guard-delivery.json` is read
- **THEN** it lists `.github/dependabot.yml`

### Requirement: Delivered workflows are updated only at their source
In each repository that receives the guard, the `github-actions` entry SHALL leave out every workflow the guard
delivers there, so Dependabot proposes no change to a delivered file. In this repository, which is their source, the
entry SHALL cover them. The list left out SHALL be taken from the guard's delivered files.

#### Scenario: troupe leaves out the delivered workflows
- **WHEN** troupe's `github-actions` entry is read
- **THEN** it leaves out `.github/workflows/guard.yml` and `.github/workflows/claude-review.yml`

#### Scenario: infrastructure covers them
- **WHEN** infrastructure's `github-actions` entry is read
- **THEN** it leaves out nothing

#### Scenario: A newly delivered workflow is left out too
- **WHEN** a workflow is added to the guard's delivered files
- **THEN** troupe's and website's generated `github-actions` entries leave it out, with no other edit

#### Scenario: Dependabot proposes no change to a delivered workflow
- **WHEN** an action pinned in a delivered workflow has a newer release, older than the cooldown
- **THEN** no Dependabot pull request in troupe or website changes that delivered workflow

### Requirement: OpenTofu provider updates are covered or recorded as manual
infrastructure SHALL have an `opentofu` entry for its provider lockfile when Dependabot is shown to update a lockfile
whose providers come from `registry.opentofu.org`. Its label SHALL be declared like the other ecosystems' labels.
If Dependabot isn't shown to, there SHALL be no such entry, and the docs SHALL say provider updates are manual.

#### Scenario: Provider updates, when Dependabot supports them
- **WHEN** a throwaway repository shows that Dependabot's `opentofu` updates open a pull request that changes
  `.terraform.lock.hcl` for a `registry.opentofu.org` provider
- **THEN** infrastructure's generated configuration has an `opentofu` entry for `/tofu`, with a declared label

#### Scenario: Provider updates, when it doesn't
- **WHEN** the throwaway repository shows no such pull request
- **THEN** infrastructure's generated configuration has no `opentofu` entry, and `docs/development-workflow.md` says
  provider updates are made by hand
