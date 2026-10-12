# Spec Delta

## MODIFIED Requirements

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
