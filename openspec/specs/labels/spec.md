# labels Specification

## Purpose

Declares each managed repository's complete set of issue labels (name, colour and description) so labels are
changed through pull requests and labels made by hand show up as drift.

## Requirements

### Requirement: Each managed repository's labels are declared in full
Each managed repository's labels SHALL be declared as a complete set: name, colour and description. A label on
GitHub that isn't declared, or that differs from its declaration, SHALL appear in the plan.

#### Scenario: A label added by hand shows as drift
- **WHEN** someone adds a label to a managed repository on GitHub
- **THEN** the next plan shows that label being removed

#### Scenario: A label's colour changed by hand shows as drift
- **WHEN** someone changes a declared label's colour on GitHub
- **THEN** the next plan shows the colour changing back

### Requirement: Adopted labels match GitHub exactly
The labels declared when a repository is adopted SHALL be the labels it had at that moment, unchanged, including
GitHub's default labels and troupe's `cap:*` labels.

#### Scenario: troupe's labels are adopted unchanged
- **WHEN** troupe's labels are adopted and a plan runs
- **THEN** the plan shows no change to any of troupe's labels
