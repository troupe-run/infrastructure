# Design

## Context

`tofu/auto_merge.tf` declares `local.auto_merge_switches`, one `github_actions_variable.auto_merge` per repository,
all `dry-run` since #359. `scripts/auto_merge.py` reads each repository's variable on every run, so the switch takes
effect on the first run after main's apply, with no workflow change. See proposal.md for why now.

## Goals / Non-Goals

**Goals:**
- The plan changes exactly the three `AUTO_MERGE` values, in place.
- The switch's value is held by a test, so it can't drift by an unreviewed edit.

**Non-Goals:**
- The rule itself, its limits and protected list (infrastructure#427).
- Removing `dry-run` as a mode: it stays useful for a repository that needs watching again.

## Decisions

- **D1: One change, all three at once.** The owner chose "on everywhere". Staggering (one repository first) was the
  alternative; the tally already covered all three, and `off` on GitHub stops any one at once.
- **D2: The test reads the declaration as text.** Like `test_main_only_environments.py`, a test reads
  `tofu/auto_merge.tf` and checks `auto_merge_switches` is exactly `{troupe, infrastructure, website}` all `on`.
  Running `tofu` in the test was the alternative; text is enough for a literal map and keeps the test fast.
- **D3: The dry-run comment keeps its marker, loses "the dry-run week".** The marker
  `<!-- auto-merge:dry-run <sha> -->` stays, since once-per-head depends on it. Only the closing line changes to
  "queue it by hand as usual".
- **D4: #363 rides along.** Dropping the ignored input changes nothing the token can do: the 2026-11-19 probe and
  every dry-run run since read `AUTO_MERGE` with the line ignored. The test's mapping skips `actions_variables`
  with the reason, as it already skips `metadata`. The first run after the apply confirms all three variables read
  (no `error` verdict for a repository).

## Risks / Trade-offs

- [A wrong rule queues something unsafe] → the merge group's checks still run; `hold` takes a pull request out; `off`
  on GitHub stops a repository at once.
- [The token can't read a variable without the dropped line] → shown at once as an `error` in the run's summary for
  that repository, which queues nothing there; restore the line (it was ignored anyway, so that can't be the cause) or
  look at the App's permissions.

## Migration Plan

1. The pull request's plan shows the three variables changing `dry-run` → `on`; the owner approves it.
2. After the merge, main's `tofu` apply sets them, once the owner approves.
3. The next `auto-merge.yml` run's summary is read: qualifying pull requests show "queued", none "commented".
4. Rollback: a pull request setting the values back to `dry-run`, or `off` on GitHub for the break-glass.
