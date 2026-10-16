# rulesets Specification

## Purpose
The rules GitHub enforces on the org's branches, declared here: which repositories and branches they cover, what they
refuse, who may bypass them, and how the owner keeps the ability to change them.

## Requirements

### Requirement: Main is protected on every managed repository except .github
`main` SHALL be covered by a ruleset on `troupe`, `infrastructure` and `website`, and on every repository brought
under management later unless its declaration says otherwise. `troupe-run/.github` SHALL be covered by its own
ruleset instead, under which only the infrastructure App changes `main`.

#### Scenario: Every protected repository has the ruleset
- **WHEN** the managed repositories' rulesets are read from GitHub
- **THEN** `troupe`, `infrastructure` and `website` each have an active ruleset on `main`, `.github` has its own
  active ruleset on `main`, and the plan shows no difference from the declaration

### Requirement: Changes reach main only through a pull request
A push directly to `main` SHALL be refused for everyone, the owner included (`.github` excepted: see below). A
pull request SHALL be mergeable without an approving review, because the org has one maintainer. The infrastructure
App is excepted:
- in a repository that receives the guard, it MAY push its deliveries straight to `main`;
- in this repository, it MAY push the encrypted state straight to `main` after an apply.

#### Scenario: A direct push is refused
- **WHEN** anyone, the owner included, pushes a commit directly to `main`
- **THEN** GitHub refuses the push, naming the ruleset

#### Scenario: A pull request merges without a review
- **WHEN** a pull request into `main` has no reviews, its required checks have passed, and it is merged by rebase
- **THEN** the merge succeeds

#### Scenario: The App delivers to a governed repository
- **WHEN** the infrastructure App commits a delivered file to `main` in a repository that receives the guard
- **THEN** GitHub accepts the commit, although the commit has no checks of its own

#### Scenario: The App commits state to this repository
- **WHEN** the infrastructure App commits `tofu/terraform.tfstate` to `main` in this repository
- **THEN** GitHub accepts the commit, although the commit has no checks of its own

#### Scenario: The App's exception is limited to governed repositories
- **WHEN** the managed rulesets are read
- **THEN** only this repository's ruleset, `.github`'s ruleset and the rulesets of repositories that receive the
  guard name the App as a bypass actor, and no other App is named by any

### Requirement: Pull requests merge by rebase only
A pull request into `main` SHALL be mergeable only by rebase. Merging with a merge commit or by squashing SHALL be
refused, so `main` keeps a linear history that carries each commit.

#### Scenario: A merge commit is refused
- **WHEN** a pull request into `main` is merged with the merge method
- **THEN** GitHub refuses it

#### Scenario: A squash is refused
- **WHEN** a pull request into `main` is merged with the squash method
- **THEN** GitHub refuses it

### Requirement: Main's history can't be rewritten or deleted
A force-push to `main` and the deletion of `main` SHALL be refused, and a merge commit SHALL NOT be pushed to it.

#### Scenario: A force-push is refused
- **WHEN** anyone force-pushes to `main`
- **THEN** GitHub refuses it

#### Scenario: Deleting main is refused
- **WHEN** anyone deletes the `main` branch
- **THEN** GitHub refuses it

### Requirement: The owner bypasses rules only through a pull request
An org owner SHALL be able to merge a pull request that a rule would otherwise block, including one whose required
checks have failed or not reported. That bypass SHALL NOT extend to pushing to `main` directly. On `.github`, the
owner has no bypass: the break-glass there is changing the ruleset.

#### Scenario: The owner's direct push is refused
- **WHEN** an org owner pushes directly to `main`
- **THEN** GitHub refuses the push

#### Scenario: The owner merges past a failing check
- **WHEN** a required check on a pull request has failed and an org owner merges it, choosing to bypass the rules
- **THEN** the merge succeeds

### Requirement: The owner can't be locked out
An org owner SHALL always be able to change or disable a ruleset on GitHub as a break-glass. Any such change SHALL
appear in the next plan, and an apply SHALL restore the declared ruleset.

#### Scenario: A ruleset disabled on GitHub shows as drift and is restored
- **WHEN** an owner disables a declared ruleset on GitHub
- **THEN** the next plan shows it returning to `active`, and applying that plan restores it

### Requirement: Pull requests merge only when their required checks pass
A pull request into `main` SHALL NOT be mergeable until every check its repository requires has passed on the pull
request's latest commit. Each required check SHALL be accepted only from the App that is meant to post it, so a check
of the same name posted by anything else doesn't count. A check that is skipped SHALL count as passed.

#### Scenario: A failing check blocks the merge
- **WHEN** one of a repository's required checks has failed on a pull request
- **THEN** GitHub refuses to merge it, naming the check

#### Scenario: A missing check blocks the merge
- **WHEN** a required check hasn't reported on a pull request's latest commit
- **THEN** GitHub refuses to merge it until the check passes

#### Scenario: A check from the wrong source doesn't count
- **WHEN** a status with a required check's name is posted on a pull request by something other than that check's App
- **THEN** the check is still missing, and the pull request can't be merged

### Requirement: Each repository requires its own checks
Each repository with a `main` ruleset SHALL require the checks that run on its pull requests:
- `infrastructure`: its CI check, each guard-tests job, the `guard` check, DCO, and its pull request's plan;
- `troupe`: each of its CI check jobs, the `guard` check and DCO;
- `website`: its CI test and the `guard` check. It SHALL NOT require DCO: its contributions are accepted under its
  own licences, with no sign-off (owner, 2026-10-16).

The required names SHALL be declared in one place.

#### Scenario: The declared names match this repository's workflows
- **WHEN** this repository's tests run
- **THEN** they fail if `infrastructure`'s required checks name a job its workflows don't define, or leave out a job
  the list above says is required

#### Scenario: A renamed job can't be merged past
- **WHEN** a pull request renames a required job, so the old name never reports
- **THEN** the pull request can't be merged until the required checks are changed to match, or the owner bypasses
  the rules

#### Scenario: A website pull request needs the guard check
- **WHEN** a pull request into the website's `main` has passed its CI test but its `guard` check has failed or not
  reported
- **THEN** GitHub refuses to merge it, naming the `guard` check

#### Scenario: A website pull request needs no sign-off
- **WHEN** a pull request into the website's `main` has unsigned-off commits and its CI test and `guard` check have
  passed
- **THEN** the merge succeeds

### Requirement: Only the App changes .github's main
In `troupe-run/.github`, every change to `main` SHALL be refused unless the infrastructure App makes it. That
includes pushes, merges of pull requests, force-pushes and deleting the branch, by anyone, org owners included.

#### Scenario: The App syncs a file
- **WHEN** the infrastructure App commits a file to `.github`'s `main`
- **THEN** GitHub accepts the commit

#### Scenario: The owner's push is refused
- **WHEN** an org owner pushes a commit to `.github`'s `main`
- **THEN** GitHub refuses it, naming the ruleset

#### Scenario: A pull request can't merge
- **WHEN** anyone, an org owner included, tries to merge a pull request into `.github`'s `main`
- **THEN** GitHub refuses the merge
