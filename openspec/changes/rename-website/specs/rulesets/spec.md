# Spec Delta

## MODIFIED Requirements

### Requirement: Main is protected on every managed repository except .github
`main` SHALL be covered by a ruleset on `troupe`, `infrastructure` and `website`, and on every repository brought
under management later unless its declaration says otherwise. `troupe-run/.github` is excluded until its own ruleset
is declared.

#### Scenario: Every protected repository has the ruleset
- **WHEN** the managed repositories' rulesets are read from GitHub
- **THEN** `troupe`, `infrastructure` and `website` each have an active ruleset on `main`, and the plan shows no
  difference from the declaration
