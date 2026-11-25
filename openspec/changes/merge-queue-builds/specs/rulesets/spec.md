# Spec Delta

## ADDED Requirements

### Requirement: A queue builds only as many entries as its CI can finish in time
Each repository whose queue is on SHALL declare, in one place, how many queued pull requests its queue tests at once
and how long it waits for a required check to report. They SHALL be sized so that an entry's checks, including the
wait for runners shared across the org, report within the wait. troupe's queue SHALL test 2 entries at once and wait
120 minutes; infrastructure's and website's SHALL test 5 and wait 60.

#### Scenario: troupe's ruleset reads its limits
- **WHEN** troupe's `protect main` ruleset is read from GitHub
- **THEN** its merge queue builds at most 2 entries at once, waits 120 minutes for a check, merges at most 5 entries
  together, and the plan shows no difference

#### Scenario: infrastructure's and website's rulesets keep theirs
- **WHEN** the `protect main` ruleset of infrastructure or website is read from GitHub
- **THEN** its merge queue builds at most 5 entries at once and waits 60 minutes for a check, and the plan shows no
  difference

#### Scenario: A third queued pull request on troupe waits its turn
- **WHEN** three pull requests are queued on troupe at once
- **THEN** the queue runs checks on the first two entries only, and starts the third's when one of them leaves the
  queue
