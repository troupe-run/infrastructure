# rulesets Specification

## Purpose
The rules GitHub enforces on the org's branches, declared here: which repositories and branches they cover, what they
refuse, who may bypass them, and how the owner keeps the ability to change them.

## Requirements

### Requirement: Main is protected on every managed repository except .github
`main` SHALL be covered by a ruleset on `troupe`, `infrastructure` and `troupe-run.github.io`, and on every repository
brought under management later unless its declaration says otherwise. `troupe-run/.github` is excluded until its own
ruleset is declared.

#### Scenario: Every protected repository has the ruleset
- **WHEN** the managed repositories' rulesets are read from GitHub
- **THEN** `troupe`, `infrastructure` and `troupe-run.github.io` each have an active ruleset on `main`, and the plan
  shows no difference from the declaration

### Requirement: Changes reach main only through a pull request
A push directly to `main` SHALL be refused for everyone, the owner included. A pull request SHALL be mergeable
without an approving review, because the org has one maintainer. There are two exceptions, both for the
infrastructure App:
- in a repository that receives the guard from this repository, it MAY push its deliveries straight to `main`;
- in this repository, it MAY push the encrypted state straight to `main` after an apply.

#### Scenario: A direct push is refused
- **WHEN** anyone, the owner included, pushes a commit directly to `main`
- **THEN** GitHub refuses the push, naming the ruleset

#### Scenario: A pull request merges without a review
- **WHEN** a pull request into `main` has no reviews and is merged by rebase
- **THEN** the merge succeeds

#### Scenario: The App delivers to a governed repository
- **WHEN** the infrastructure App commits a delivered file to `main` in a repository that receives the guard
- **THEN** GitHub accepts the commit

#### Scenario: The App commits state to this repository
- **WHEN** the infrastructure App commits `tofu/terraform.tfstate` to `main` in this repository
- **THEN** GitHub accepts the commit

#### Scenario: The App's exception is limited to governed repositories
- **WHEN** the managed rulesets are read
- **THEN** only this repository's ruleset and the rulesets of repositories that receive the guard name the App as a
  bypass actor, and the read-only plan App is named by none

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
An org owner SHALL be able to merge a pull request that a rule would otherwise block. That bypass SHALL NOT extend
to pushing to `main` directly.

#### Scenario: The owner's direct push is refused
- **WHEN** an org owner pushes directly to `main`
- **THEN** GitHub refuses the push

### Requirement: The owner can't be locked out
An org owner SHALL always be able to change or disable a ruleset on GitHub as a break-glass. Any such change SHALL
appear in the next plan, and an apply SHALL restore the declared ruleset.

#### Scenario: A ruleset disabled on GitHub shows as drift and is restored
- **WHEN** an owner disables a declared ruleset on GitHub
- **THEN** the next plan shows it returning to `active`, and applying that plan restores it
