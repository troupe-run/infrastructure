## ADDED Requirements

### Requirement: Only Dependabot creates or updates its branches
Each repository that gets a `.github/dependabot.yml` SHALL have a ruleset that refuses creating and updating any
branch whose name starts with `dependabot/` to everyone but Dependabot, with no bypass for org owners. It SHALL NOT
refuse Dependabot's force-push, since Dependabot rewrites its branch when it rebases, and SHALL NOT refuse deletion,
so delete-on-merge removes the branch. A change to the ruleset on GitHub SHALL show in the next plan.

#### Scenario: Every repository with a configuration has the ruleset
- **WHEN** the declared rulesets are read
- **THEN** troupe, website and infrastructure each have one covering `refs/heads/dependabot/**/*`, refusing creation
  and update, whose only bypass actor is Dependabot, and `.github` has none

#### Scenario: An owner creates a Dependabot branch
- **WHEN** an org owner pushes a new branch named `dependabot/npm_and_yarn/anything` to website
- **THEN** GitHub refuses the push

#### Scenario: An owner writes to a Dependabot branch
- **WHEN** an org owner pushes a commit to an existing Dependabot branch, or uses "Update branch" on its pull
  request
- **THEN** GitHub refuses it, and the branch is unchanged

#### Scenario: Dependabot opens and rebases its pull requests
- **WHEN** Dependabot opens a pull request for an update, and later rebases it when asked with `@dependabot rebase`
- **THEN** GitHub allows both the new branch and the force-push

#### Scenario: A merged Dependabot pull request
- **WHEN** a Dependabot pull request is merged, with delete-on-merge on
- **THEN** GitHub deletes its branch

#### Scenario: The ruleset is changed on GitHub
- **WHEN** someone adds a bypass actor to a repository's Dependabot ruleset on GitHub
- **THEN** the next plan shows the ruleset returning to its declared bypass actors
