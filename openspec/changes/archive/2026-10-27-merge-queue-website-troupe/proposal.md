# Proposal

Issue: #197, the follow-up from #169's `merge-queue` change.

## Why

`merge-queue` put infrastructure's `main` behind a merge queue and added a switch per repository (`merge_queue` in
`tofu/repositories.tf`). website and troupe stayed off because their own CI didn't report on merge groups yet (merge-queue
design D6, D7). Until they're on, two pull requests there can each pass and still break `main` together, which is the
problem #169 set out to fix.

Both are ready now:

- **website:** troupe-run/website#69 was done by troupe-run/website#70 (50a1713). `test` runs the whole check on
  `merge_group`.
- **troupe:** troupe-run/troupe#180 was done by troupe-run/troupe#183. `check` runs the full check on `merge_group`,
  and troupe's `scripts/tests/test_ci_workflow.py` fails if anything filters it.

Their other required checks already report there: `guard (workflow rules)` arrives by delivery, running on
`merge_group`, and `DCO` reported on merge groups in the probe and reports on infrastructure's merge groups now.

## What Changes

- **Turn on website's and troupe's queues together, in one pull request** (`merge_queue = true` on `repo_website`
  and `repo_troupe`). #197 asked for one pull request each, website first. That order was set while troupe's CI
  wasn't ready yet. Both are ready now, and the owner chose one change for both (2026-10-27, design D1).
- **The plan shows only the queue:** each repository's `protect main` ruleset gains the `merge_queue` block of
  merge-queue design D2, and `allow_auto_merge` turns on. Nothing else changes.
- **Proof after the apply:** the next pull request in each repository lands through its queue, with every check it
  requires reporting on the merge group. Rollback is that repository's switch, turned off in a pull request the owner
  merges with `--admin` if the queue is stuck (merge-queue Migration Plan).
- **Docs and comments stop saying "infrastructure first, then website and troupe"** (README, the module comments in
  `tofu/repositories.tf`).
- **website's and troupe's own CLAUDE.md** still describe the merge step as "merged by rebase" (website) or say
  nothing about it (troupe). Those files are theirs, so this change opens an issue in each rather than editing them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `rulesets`: adds a requirement naming which repositories merge through the queue (troupe, infrastructure and
  website), and how a product repository's readiness is checked before its switch goes on.

## Impact

- `tofu/repositories.tf`: two `merge_queue = true` lines and their comments.
- `README.md`: the merge-queue bullet.
- GitHub: website's and troupe's `protect main` rulesets and repository settings, after the owner approves the plan.
- troupe and website: every pull request, Dependabot's and release-please's included, lands through the queue from
  the apply on. An issue in each for its CLAUDE.md wording.
- Not changed: `org-profile/CONTRIBUTING.md` already says "through the repository's merge queue where it has one",
  which stays true, so `.github` gets no commit from this plan.
