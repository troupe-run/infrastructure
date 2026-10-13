# Spec Delta

## ADDED Requirements

### Requirement: Main is planned every day
CI SHALL plan `main` once a day, whether or not anything merged. The plan SHALL be shown, and a plan with changes
SHALL wait for the owner's approval and apply as any plan of `main` does. A plan with no changes SHALL end the run
without asking for approval. The daily plan SHALL run whatever commit `main`'s head is, the App's state commit
included.

#### Scenario: Drift shows within a day
- **WHEN** a managed file or setting is changed on GitHub outside a delivery or an apply, and nothing merges
  afterwards
- **THEN** within a day, a run on `main` shows a plan restoring it and waits for the owner's approval

#### Scenario: The state commit is planned too
- **WHEN** the daily plan runs and `main`'s head is the App's state commit after an apply
- **THEN** the run plans `main` rather than skipping

#### Scenario: No drift asks nothing
- **WHEN** the daily plan finds the declaration and the org in agreement
- **THEN** the run ends after the plan, with no approval requested
