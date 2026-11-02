# Spec Delta

## ADDED Requirements

### Requirement: The list of issues with no milestone is read with a token that can see issues
Both plan jobs SHALL read the list with a token minted from the troupe-run-infrastructure App, limited to the
milestone repositories and to reading issues. They SHALL NOT read it with the job's `GITHUB_TOKEN`, which can't see
issues on the other repositories, and SHALL NOT give the job's `GITHUB_TOKEN` a new permission for it.
`scripts/check.py` SHALL fail when either job reads the list with another token or one that can do more.

#### Scenario: A milestone-closing plan on a pull request
- **WHEN** a pull request closes a milestone while troupe has open issues with no milestone, and its plan runs
- **THEN** the plan's comment lists those issues under troupe, not "none"

#### Scenario: The step goes back to the job's token
- **WHEN** a change makes either job's "Issues with no milestone" step read with `${{ github.token }}`
- **THEN** `scripts/check.py` fails, naming the job and the token to use

#### Scenario: The token is widened
- **WHEN** a change gives the minted token another permission, or a repository that isn't a milestone repository
- **THEN** `scripts/check.py` fails, naming what was added

### Requirement: A list read with a token that can't see issues fails
For each repository with issues on, the step SHALL compare what it read with a count GitHub keeps whatever the
token can see, and SHALL fail, naming the repository, how many it read and how many GitHub counts, when it read
fewer. It SHALL NOT then show any list. This holds whichever token the step is given.

#### Scenario: A token that sees only pull requests
- **WHEN** a plan closes a milestone, and the token reading troupe sees its open pull requests but none of its 14
  open issues
- **THEN** the step fails naming troupe and both counts, and no comment says troupe has no issues with no milestone

#### Scenario: Every open issue and pull request is seen
- **WHEN** the step reads as many as GitHub counts in each repository
- **THEN** it lists the issues with no milestone as before, and doesn't fail
