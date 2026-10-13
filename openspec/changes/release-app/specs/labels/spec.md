# Spec Delta

## ADDED Requirements

### Requirement: troupe has release-please's labels
troupe's label set SHALL include `autorelease: pending` and `autorelease: tagged`, declared once in their own set
with a colour and a description, because release-please finds its release pull request by these labels and a label
it made by itself would be removed by the next apply. No other repository SHALL get them until it releases.

#### Scenario: The labels are created on troupe
- **WHEN** a plan runs after the release labels are declared
- **THEN** it shows `autorelease: pending` and `autorelease: tagged` being created on troupe-run/troupe with the
  declared colour and description, and no other label on any repository changing

#### Scenario: A release label edited by hand
- **WHEN** someone changes the colour or description of `autorelease: pending` on troupe on GitHub
- **THEN** the next plan shows it changing back, and the label stays on every pull request that carries it

#### Scenario: Another repository
- **WHEN** a plan runs for infrastructure, `.github` or website
- **THEN** it shows no `autorelease:` label on them
