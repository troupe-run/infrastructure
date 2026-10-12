# Spec Delta

## MODIFIED Requirements

### Requirement: The workflow's templates are org defaults
The pull request template and the issue forms (Bug, Feature and Decision) SHALL have their source in this repository
and be published to `troupe-run/.github` as the org's defaults. They SHALL describe the workflow in the order this
spec gives it, and SHALL NOT name a particular repository's product, so they suit any repository in the org.

#### Scenario: A repository with no templates of its own
- **WHEN** someone opens a pull request, or a new issue, in a troupe-run repository with no `.github/ISSUE_TEMPLATE/`
  and no pull request template of its own
- **THEN** the pull request's description starts from the org's template, and the issue chooser offers the Bug,
  Feature and Decision forms

#### Scenario: The PR template gives the settled order
- **WHEN** someone reads the pull request template
- **THEN** it says to archive the change on the branch before merging, and after the merge to comment on the issue
  with the pull request and the archived change

#### Scenario: The forms set the issue's type
- **WHEN** someone files an issue with the Bug, Feature or Decision form
- **THEN** the issue gets the matching issue type, and a Decision issue also gets the `needs:owner` label

#### Scenario: A form names something that doesn't exist
- **WHEN** a form names an issue type the org doesn't declare, or a label that isn't declared for every managed
  repository
- **THEN** the repository's checks fail and name the form and the missing type or label

#### Scenario: Vulnerability reports go to the security policy
- **WHEN** someone opens the issue chooser in a repository using the org's forms
- **THEN** it offers a blank issue and exactly one entry for reporting a vulnerability: GitHub's own, shown because
  the org publishes a security policy

#### Scenario: The chooser config doesn't duplicate GitHub's security entry
- **WHEN** the org's chooser config adds a contact link to the security policy
- **THEN** the repository's checks fail and say GitHub already shows that entry
