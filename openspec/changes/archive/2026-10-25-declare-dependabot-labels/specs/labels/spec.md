## ADDED Requirements

### Requirement: Each repository has the labels Dependabot applies
Each managed repository's label set SHALL include `dependencies` and the label Dependabot applies for each package
ecosystem its dependency graph lists. Each label SHALL be declared once, with the name, colour and description that
GitHub's Dependabot gives it. Dependabot then finds the labels and creates none of its own. A repository whose
dependency graph lists no ecosystem SHALL get none of them.

#### Scenario: website's Dependabot labels are kept
- **WHEN** website's `dependencies` and `javascript` labels, which Dependabot created, are declared and a plan runs
  while its Dependabot pull requests are open
- **THEN** the plan shows no change to either label on website, and the pull requests keep their labels

#### Scenario: The labels are created where Dependabot hasn't run
- **WHEN** a plan runs after the Dependabot labels are declared
- **THEN** it shows `github_actions` created on website, and `dependencies`, `python:uv` and `github_actions`
  created on troupe and infrastructure, each with the declared colour and description, and no other label changing

#### Scenario: A repository with no dependencies
- **WHEN** a plan runs for `.github`, whose dependency graph lists nothing
- **THEN** it shows no Dependabot label on `.github`

#### Scenario: A repository names an ecosystem that isn't declared
- **WHEN** a repository's label set names a Dependabot ecosystem that the Dependabot set doesn't declare
- **THEN** `scripts/check.py` fails, naming the repository and the ecosystem

#### Scenario: A Dependabot label's description over GitHub's limit
- **WHEN** a declared Dependabot label's description is longer than 100 characters
- **THEN** `scripts/check.py` fails, naming the label and its length
