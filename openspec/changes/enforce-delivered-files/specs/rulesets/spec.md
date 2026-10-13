# Spec Delta

## ADDED Requirements

### Requirement: Only the App changes a delivered file in a governed repository
In each repository that receives the guard, GitHub SHALL refuse any push or API edit that changes a delivered file
(each file the delivered list names, the list included), on any branch, unless the infrastructure App makes it.
Nobody else SHALL bypass this rule, org owners included. The restricted paths SHALL be the delivered files,
declared in one place.

#### Scenario: A push that changes a delivered file is refused
- **WHEN** anyone other than the App, an org owner included, pushes a branch to `troupe` carrying a commit that
  changes `scripts/guard.py`, whatever the commit's author says
- **THEN** GitHub refuses the push, naming the ruleset and the path

#### Scenario: An edit through GitHub is refused
- **WHEN** anyone other than the App commits a change to `.github/workflows/guard.yml` in `troupe` through GitHub's
  web editor or its contents API
- **THEN** GitHub refuses the commit

#### Scenario: The App's delivery lands
- **WHEN** the infrastructure App commits a delivered file to `troupe`'s `main`
- **THEN** GitHub accepts the commit

#### Scenario: Other files are unaffected
- **WHEN** a contributor pushes a branch to `troupe` that changes no delivered file
- **THEN** this rule doesn't refuse it

#### Scenario: The restricted paths follow the delivered files
- **WHEN** a file is added to or removed from the guard's delivered files, and the plan is applied
- **THEN** the ruleset restricts exactly the delivered files, with no separate list to update

## MODIFIED Requirements

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
  guard (their `main` ruleset and their delivered-files ruleset) name the App as a bypass actor, and no other App is
  named by any
