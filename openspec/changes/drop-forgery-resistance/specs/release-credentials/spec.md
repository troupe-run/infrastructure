## ADDED Requirements

### Requirement: Only the release App creates or updates release branches
troupe SHALL have a ruleset that refuses the creation and update of any `release-please--*` branch to everyone but
the release App, with no bypass for org owners. It SHALL NOT refuse the release App's force-push, because
release-please rewrites its branch as `main` moves. It SHALL NOT refuse deletion, so GitHub's delete-on-merge removes
the branch once its pull request merges. A change to the ruleset on GitHub SHALL show in the next plan.

#### Scenario: An owner creates a release branch
- **WHEN** an org owner pushes a new branch named `release-please--anything` to troupe
- **THEN** GitHub refuses the push

#### Scenario: An owner writes to a release branch
- **WHEN** an org owner pushes or force-pushes to an existing `release-please--*` branch on troupe
- **THEN** GitHub refuses it, and the branch is unchanged

#### Scenario: The release App writes its branch
- **WHEN** the release App creates, updates or force-updates a `release-please--*` branch on troupe
- **THEN** GitHub allows it

#### Scenario: A merged release pull request
- **WHEN** a pull request from a `release-please--*` branch on troupe is merged, with delete-on-merge on
- **THEN** GitHub deletes the branch, and only the release App can create it again

#### Scenario: Other branches are unaffected
- **WHEN** anyone with write access pushes a branch with any other name, such as one named after an OpenSpec change
- **THEN** this ruleset doesn't refuse it

#### Scenario: The ruleset is changed by hand
- **WHEN** someone disables the ruleset, or adds a bypass actor to it, on GitHub
- **THEN** the next plan shows the change, and applying it restores the declared ruleset

## REMOVED Requirements

### Requirement: Only the release App writes release branches
**Reason**: It refused deletion too, which stopped GitHub's delete-on-merge removing the release branch after its pull
request merged. The owner wants the branch removed (2026-10-15). Reserving creation is enough for the name to be
proof: a deleted branch can only come back from the App.
**Migration**: Replaced by "Only the release App creates or updates release branches". The plan updates troupe's
"release branches" ruleset in place, dropping its `deletion` rule. The release branch now goes when its pull request
merges, and release-please creates it again for the next release.
