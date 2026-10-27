# Design

## Context

`tofu/modules/repository` already has the `merge_queue` switch (merge-queue design D2). It adds the queue rule to the
`protect main` ruleset and sets `allow_auto_merge`. It's on for `repo_infrastructure` only. infrastructure's
`scripts/tests/test_required_checks.py` checks that every check infrastructure requires runs on `merge_group` before
that switch can be on. It reads this repository's workflows, so it can't see troupe's or website's.

What those two repositories require (`tofu/required-checks.json`), and where each check reports on merge groups:

| Repository | Check | Runs on `merge_group` because |
|---|---|---|
| website | `test` | `ci.yml` on website's `main`, since website#70 (50a1713) |
| website | `guard (workflow rules)` | the delivered `guard.yml` (merge-queue D3) |
| troupe | `check` | `ci.yml` on troupe's `main`, since troupe#183. `changes` runs only on pull requests, so a merge group runs everything. troupe's `test_ci_workflow.py` guards that |
| troupe | `guard (workflow rules)` | the delivered `guard.yml` |
| troupe | `DCO` | the DCO App, confirmed in the probe and on infrastructure's merge groups |

## Goals / Non-Goals

**Goals:**

- Turn both switches on in one plan that changes nothing else.
- Prove each queue with that repository's next real pull request.

**Non-Goals:**

- No change to the queue's settings (D2's values stay the same everywhere).
- No change to troupe's or website's files. Their CLAUDE.md wording goes to an issue in each.
- No test here that reads another repository's workflows over the network. The guard and tests work offline.

## Decisions

### D1. Both repositories in one change and one apply

#197 asked for website first, then troupe, each in its own pull request. That staging was there because troupe's
`check` wasn't ready. Both are ready now. The owner chose (2026-10-27) one change, `merge-queue-website-troupe`, for
both.

What the staging would have bought is a working website queue before troupe's goes on. infrastructure's queue already
proves the module, the DCO App and the delivered guard on merge groups. What's new for each repository is only its
own CI workflow, and the two are independent. So a stall in one doesn't say anything about the other, and each is
rolled back on its own.

**Alternative: two changes, website first.** Two issues' worth of process, two plan approvals and two applies for two
lines, with nothing learned from the first that the second needs.

### D2. Readiness is checked at turn-on, not by a test here

For infrastructure, a test fails if the switch is on while a required workflow lacks `merge_group`. troupe's and
website's workflows aren't in this repository, so the same test can't run offline. Instead:

- before the switch goes on, a task reads each required check's workflow from that repository's `main`
  (`gh api .../contents/.github/workflows/ci.yml`) and confirms `merge_group` is a trigger and nothing narrows the run
  on it;
- after that, each repository guards its own workflow: troupe's `test_ci_workflow.py` already fails if `check` is
  filtered on merge groups.

**Alternative: a test here pinning `merge_queue_modules()` to all three repositories.** It checks a config value
against itself, not a property. It would also fail the switch-off pull request, the rollback, which must be one line
the owner can merge quickly.

### D3. The proof is each repository's next pull request

Open pull requests in both repositories (Dependabot's, troupe's release-please `chore: release main`, website#52) are
real pull requests that would land through the queue. Whichever the owner merges first in each repository after the
apply is the proof: it joins the queue, every required check reports on its merge group, and `main`'s head becomes
the tested commit. No probe pull request is opened in a live repository.

## Risks / Trade-offs

- [A product repository's CI doesn't report on the merge group after all] → the pull request leaves the queue at the
  60-minute timeout and `main` is unchanged. One pull request turns that repository's switch off, merged with
  `gh pr merge --rebase --admin` if the queue holds it (merge-queue Migration Plan).
- [A Dependabot pull request's commits carry no sign-off, and troupe requires `DCO` in the queue] → the DCO App
  treats Dependabot's commits the same on a merge group as on the pull request, where they pass today. The first
  queued Dependabot pull request in troupe is checked for it. If DCO fails there, troupe's switch goes off and it goes
  back to the owner on #197.
- [troupe's release-please pull request lands through the queue] → release-please reads `main` after the push, so the
  tested commit it tags is the one that landed. It's watched on the first release after the apply.
- [Deliveries and state commits land on `main` while pull requests are queued] → the queue rebuilds and runs again.
  That costs CI time, never correctness (merge-queue risks).
- [Dependabot's pull requests stop merging with one click] → they join the queue like any other. `gh pr merge <n>` and
  "Merge when ready" both queue, since auto-merge comes on with the switch.

## Migration Plan

1. One pull request here sets both switches. Its plan shows only the two rulesets gaining the queue rule and
   `allow_auto_merge` turning on for the two repositories.
2. The owner approves the apply of `main`. Check both rulesets on GitHub show the rule with `merge_method: REBASE`.
3. Each repository's next pull request lands through the queue (D3).

Rollback is per repository: `merge_queue = false` on its module, applied after the owner approves the plan. If the
queue is stuck, the owner merges that pull request with `--admin`, or disables the rule on GitHub, which the next plan
shows as drift until the switch-off applies.
