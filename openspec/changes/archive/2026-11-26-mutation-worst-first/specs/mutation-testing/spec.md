## MODIFIED Requirements

### Requirement: A run opens a bounded number of new issues
A run SHALL open at most the declared number of issues per repository, for the lowest scores first, ties by module
name. Modules beyond that SHALL be named in the run's summary and handled by a later run. Open issues SHALL always be
updated or closed.

#### Scenario: More modules than the cap
- **WHEN** eight modules in troupe fall under the threshold and the cap is 5, with none having an issue
- **THEN** five issues are opened, the summary names the other three, and the next run opens issues for those still
  under

#### Scenario: The worst modules come first
- **WHEN** more modules than the cap fall under the threshold with no issue, at different scores
- **THEN** the lowest scores get the new issues, a tie at the cap going to the module first by name
