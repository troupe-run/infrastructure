# Design

## Context

See proposal.md, Why. The queue's parameters are written once, in the `merge_queue` block of the repository module's
`protect main` ruleset (`tofu/modules/repository/main.tf`; merge-queue design D2), with the same values for troupe,
infrastructure and website. GitHub's Free plan limits concurrent jobs per organisation, not per repository: about 5
macOS jobs at a time, shared by every repository's CI.

What each queue entry runs (2026-11-25):

| Repository | Merge-group CI | macOS legs per entry | Leg timeout | Recent merge-group runs |
|---|---|---|---|---|
| troupe | `check`: 3 OSes × Python 3.12–3.15 (12 legs), plus the guard (Linux) | 4 | 30 min | 43–84 min |
| infrastructure | `check` (Linux) and `guard tests`: 3 OSes × 3.12–3.15 less Linux 3.15 (11 legs) | 4 | 20 min | 10–33 min |
| website | `test` (Linux) and the guard (Linux) | 0 | — | — |

## Goals / Non-Goals

**Goals:**

- troupe's queue builds 2 entries at once and waits 120 minutes; the plan shows only those two values changing.
- The two values are declared per repository, next to the repository's `merge_queue` switch.

**Non-Goals:**

- Changing infrastructure's or website's queue (D4 recommends only).
- Changing troupe's CI matrix or leg timeouts.

## Decisions

### D1. Two module inputs, defaulting to today's values

The module gains `merge_queue_builds` (number, default 5) and `merge_queue_check_timeout_minutes` (number, default 60),
used for `max_entries_to_build` and `check_response_timeout_minutes`. Defaults equal to today's values mean
infrastructure's and website's rulesets plan no change. Each input validates its range, so a wrong value fails
`tofu validate` rather than the apply: builds 1–100 (GitHub refuses 101, and 0 would build nothing) and the wait 1–360
minutes (GitHub refuses 0 and 361; probe, 2026-11-25).

**Alternative: one object input for every queue parameter.** It would make each repository repeat the five values it
doesn't change, and nothing else differs between repositories yet.

**Alternative: change the module's literals.** It would change all three repositories, which the owner's decision
doesn't cover.

### D2. troupe sets 2 and 120

`tofu/repositories.tf` sets them on troupe's module call, with a comment naming infrastructure#409. 2 builds put 8
macOS legs in line instead of 20, and 120 minutes covers a 30-minute leg plus the wait for a runner (owner,
2026-11-25).

### D3. `max_entries_to_merge` stays 5

With `ALLGREEN`, a group lands only entries whose own queue commit passed, so at most the entries being built can merge
together. Building 2 caps a merge at 2 already; lowering the merge limit too changes nothing the queue does, and would
add a third value to the plan. GitHub accepts a merge limit above the build limit: a probe ruleset with 2, 5 and 120
read back unchanged (2026-11-25, tasks 1.1).

### D4. infrastructure and website: recommendation, no change

- **website** has no exposure: no merge-group job runs on macOS, and its Linux jobs take minutes.
- **infrastructure** has the same shape at a smaller size: every entry runs the guard's 4 macOS legs, and they draw on
  the same org-wide macOS runners as troupe's. Its legs are shorter (20-minute timeout, runs of 10–33 minutes), and it
  rarely queues more than two pull requests at once, so it hasn't timed out; #263's drop (2026-11-02) was a runner
  that was never acquired, not the timeout. Recommendation: leave it at 5 and 60, and apply the same two inputs
  (for example 2 and 90) if an infrastructure entry is dropped with `checks_timed_out`. It's a one-line change per
  input now.

## Risks / Trade-offs

- [A long troupe queue lands more slowly] → Each pair of entries now finishes before the next starts, but entries
  stop being dropped and re-queued, which cost more.
- [infrastructure's entries still compete with troupe's for macOS runners] → troupe's 8 legs at most, plus
  infrastructure's 4 per entry, is still above 5, so a busy moment queues for runners; 120 minutes absorbs it on troupe,
  and D4 says what to do if infrastructure times out.

## Migration Plan

Merge, then the owner approves the `apply` job of the `tofu` run on `main`. Pull requests already queued on troupe are
rebuilt under the new limits. Rollback: revert the two lines in `tofu/repositories.tf` and apply.
