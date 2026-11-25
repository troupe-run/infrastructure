# Proposal

## Why

troupe's merge queue drops pull requests with `checks_timed_out`: troupe#493 and troupe#494 were dropped this way on
2026-11-25 (infrastructure#409). The queue builds up to 5 entries at once, each runs troupe CI's 12-leg matrix with 4
macOS legs, and the Free plan runs about 5 macOS jobs at a time across the org. A late entry's legs wait for a runner,
then take up to 30 minutes each (since troupe#508), and its checks report after the queue's 60-minute timeout. The
owner decided (2026-11-25) that troupe's queue builds 2 entries at once and waits 120 minutes for checks.

## What Changes

- How many entries a repository's queue builds at once, and how long it waits for a required check, become
  per-repository inputs of the repository module. Their defaults are today's values (5 and 60), so infrastructure and
  website don't change.
- troupe's `protect main` ruleset (24895454) builds 2 entries at once (`max_entries_to_build` 5 → 2) and waits 120
  minutes (`check_response_timeout_minutes` 60 → 120). The plan shows only those two values changing.
- `max_entries_to_merge` stays 5 everywhere (design D3).
- The PR records whether infrastructure's and website's queues have the same exposure, as a recommendation only
  (design D4).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `rulesets`: a requirement that each repository's queue declares how many entries it builds at once and how long it
  waits for a check, sized to its CI, with troupe's values.

## Impact

- `tofu/modules/repository/` (two new variables, used in the `merge_queue` block) and `tofu/repositories.tf`
  (troupe's module call).
- Live: troupe's `protect main` ruleset, applied from `main` after the owner approves the plan. Pull requests already
  queued on troupe are rebuilt under the new limits.
- Throughput: troupe's queue tests at most 2 entries at once, so a long queue lands more slowly, but entries stop
  timing out and being dropped.
