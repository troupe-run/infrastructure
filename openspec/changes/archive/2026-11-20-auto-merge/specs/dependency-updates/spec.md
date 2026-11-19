# Spec Delta

## MODIFIED Requirements

### Requirement: The dispatch from troupe and website only starts the workflow
In troupe and website, the workflow that starts `dependabot-issues` SHALL run from that repository's `main` only. It
SHALL check out nothing, SHALL NOT pass anything from its triggering event to the run it starts, and SHALL do nothing
but start `dependabot-issues` or `auto-merge` on infrastructure's `main`. It SHALL be one of the guard's delivered
files.

#### Scenario: What the dispatcher does
- **WHEN** the dispatcher's workflow file is read
- **THEN** it has no checkout step, no workflow expression that reads the event beyond choosing which workflow to
  start, and its steps only start `dependabot-issues.yml` or `auto-merge.yml` in troupe-run/infrastructure on `main`

#### Scenario: The dispatcher in infrastructure
- **WHEN** a "Dependabot Updates" run completes in infrastructure, which holds the dispatcher as its source
- **THEN** the dispatcher's job is skipped there, and it uses no environment

#### Scenario: The dispatch credential is missing
- **WHEN** troupe's dispatcher runs before `DISPATCH_APP_PRIVATE_KEY` is set
- **THEN** its run fails, and a later run, the daily backstop at the latest, reports any pull request this left
  without its issue or closing line

## ADDED Requirements

### Requirement: The dispatcher starts auto-merge when a pull request changes state
In troupe and website, the dispatcher SHALL start infrastructure's `auto-merge.yml` on `main`, with no inputs, when a
run of CI, `guard` or the review completes for a pull request, and when a pull request's labels change. In
infrastructure it SHALL do nothing for these events, since `auto-merge.yml` runs on them directly.

#### Scenario: CI completes in website
- **WHEN** website's CI completes on a pull request
- **THEN** the dispatcher starts `auto-merge.yml` on infrastructure's `main`, with no inputs

#### Scenario: A hold label is added in troupe
- **WHEN** the owner adds `hold` to a troupe pull request
- **THEN** the dispatcher starts `auto-merge.yml`, which takes the pull request out of the queue if the App queued it

#### Scenario: Dependabot's run
- **WHEN** a "Dependabot Updates" run completes in troupe
- **THEN** the dispatcher starts `dependabot-issues.yml` as before, and not `auto-merge.yml`
