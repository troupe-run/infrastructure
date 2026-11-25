# Design

## Context

merge-queue-builds (#409, #410) made the queue's build count and check wait module inputs, `merge_queue_builds` and
`merge_queue_check_timeout_minutes`, with defaults 5 and 60; troupe sets 2 and 120. infrastructure uses the defaults.

## Goals / Non-Goals

**Goals:** infrastructure sets 2 and 120; the plan shows only those two values changing on its ruleset.

**Non-Goals:** website (no macOS legs, no drops), the CI matrix (#414), the module.

## Decisions

### D1. The same 120 minutes as troupe, though infrastructure's own legs are short

infrastructure's macOS legs run 3–5 minutes, but they wait in the org's one macOS line behind troupe's legs of up to
30 minutes, so its wait has to cover troupe's worst case, not its own. Its 2026-11-25 runs took up to 131 minutes end
to end at 5 builds each; at 2 builds per queue, at most 16 macOS legs are in line instead of 28.

**Alternative: 2 builds, keep 60 minutes.** Cheaper on a stuck check, but an entry behind two troupe entries' macOS
legs can still wait over an hour.

### D2. Two lines on infrastructure's module call

The same shape as troupe's, with a comment naming #413.

## Risks / Trade-offs

- [This PR itself is queued under 5 and 60] → If it's dropped with `checks_timed_out`, the owner re-queues it; no
  rebase is needed.
- [16 macOS legs still exceed ~5 runners] → Accepted; #414 is the owner's decision on the cause.
