# Proposal

## Why

infrastructure's merge queue drops pull requests the way troupe's did (#409): on 2026-11-25/26 it dropped #408 and
#386 with `checks_timed_out`, and #383 with a macOS `guard tests` leg cancelled waiting for a runner (#413). Each
entry runs 4 macOS legs. They take 3–5 minutes, but wait for the org's ~5 macOS runners behind troupe's legs, which
take up to 30 minutes, and infrastructure's merge-group runs took 82–131 minutes end to end on 2026-11-25. The owner
decided (2026-11-26) that infrastructure's queue gets troupe's limits: 2 entries at once, 120 minutes.

## What Changes

- infrastructure's `protect main` ruleset builds 2 entries at once (`max_entries_to_build` 5 → 2) and waits 120
  minutes (`check_response_timeout_minutes` 60 → 120), through the module inputs merge-queue-builds added. The plan
  shows only those two values changing.
- `max_entries_to_merge` stays 5 (merge-queue-builds D3). website keeps 5 and 60.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `rulesets`: "A queue builds only as many entries as its CI can finish in time" is replaced by "Each queue's builds
  and wait fit the org's shared runners", which gives infrastructure troupe's limits; the old scenarios named
  infrastructure as keeping 5 and 60.

## Impact

- `tofu/repositories.tf` (infrastructure's module call). No module change.
- Live: infrastructure's `protect main` ruleset, applied from `main` after the owner approves the plan. This PR itself
  goes through the queue under the old limits.
- The underlying cause, macOS legs per entry against the org-wide pool, is the owner's decision in #414.
