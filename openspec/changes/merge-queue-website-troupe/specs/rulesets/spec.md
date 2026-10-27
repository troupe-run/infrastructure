# Spec Delta

## ADDED Requirements

### Requirement: troupe, infrastructure and website merge through the queue
Each repository whose `main` takes pull requests (troupe, infrastructure and website) SHALL have its merge queue
turned on. A product repository's switch SHALL go on only once every check it requires runs on merge groups on its
`main`, since its CI workflows live in that repository and this one's tests can't read them.

#### Scenario: Each repository's ruleset has the queue
- **WHEN** the `protect main` ruleset of troupe, infrastructure or website is read from GitHub
- **THEN** it has the merge queue rule, merging by rebase, and the plan shows no difference

#### Scenario: A product repository's next pull request lands through its queue
- **WHEN** the owner merges a pull request in troupe or website after its queue is turned on
- **THEN** the pull request joins the queue, every check that repository requires reports on the merge group, and
  `main`'s new head is the commit the queue tested

#### Scenario: A product repository's CI doesn't run on merge groups
- **WHEN** the workflow defining one of troupe's or website's required checks, on that repository's `main`, isn't
  triggered by `merge_group` or narrows what it runs there
- **THEN** that repository's switch stays off until a pull request there fixes the workflow
