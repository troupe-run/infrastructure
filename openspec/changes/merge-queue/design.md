# Design

## Context

See proposal.md for why. The current state this design works from:

- `tofu/modules/repository/main.tf` declares the `protect main` ruleset (`main_ruleset = "pull-request"`) for troupe,
  infrastructure and website: rebase only, linear history, required checks from `tofu/required-checks.json`, each
  pinned to its App, with `strict_required_status_checks_policy = false` (required-checks D3). Org owners bypass on
  pull requests only. The infrastructure App bypasses `always`, for deliveries and state commits.
- The pinned provider (`integrations/github` 6.13.0) has a `rules.merge_queue` block: `merge_method`
  (`MERGE`/`SQUASH`/`REBASE`, default `MERGE`), `grouping_strategy` (`ALLGREEN`/`HEADGREEN`), `max_entries_to_build`,
  `max_entries_to_merge`, `min_entries_to_merge`, `min_entries_to_merge_wait_minutes` (default 5) and
  `check_response_timeout_minutes` (default 60).
- Required checks, by repository: infrastructure `check`, `guard tests`, `guard (workflow rules)`,
  `plan (pull request)`, `DCO`; troupe `check`, `guard (workflow rules)`, `DCO`; website `test`,
  `guard (workflow rules)`. None of the workflows behind them runs on `merge_group` today.
- `guard.yml` runs on `push` to `**` and on `pull_request`. `scripts/guard.py ci` reads the range, branch, title and
  description from the event (`github_ci_inputs`). Any event that isn't `pull_request` is read as a push.
- `tofu.yml`'s `pr-plan` job runs only on `pull_request`, in the `plan-pr` environment, which the owner approves.
  Its concurrency group is `tofu-pr-<n>` for a pull request and `tofu-main` for everything else.
- The DCO App says it has supported merge groups since July 2026 (dcoapp/app#292, fixed in #303). Its installation
  here already holds `merge_queues: read` (`oob/app-installations.json`). dcoapp/app#311 reports DCO failing in
  queues that squash. We rebase, which keeps each commit and its sign-off.

## Goals / Non-Goals

**Goals:**
- `main` in each governed repository only ever holds a combination its required checks passed on.
- The owner's merge click stays the only manual step per pull request. The queue adds no approval.
- A repository's queue can be turned on and off by one declared value, so a repository whose checks can't report on
  the queue yet is left as it is.

**Non-Goals:**
- Strict up-to-date checks. They stay off (required-checks D3 holds). The queue does what strict would.
- Running `main`'s CI once instead of twice. The queue's run and `main`'s run test the same tree. `main`'s run stays,
  because the App's state commits and deliveries reach `main` outside the queue, and `plan (main)` and guard
  delivery both follow CI on `main`. Deduplicating them is a later change if the cost shows.
- The `release branches` ruleset and `.github`'s `app only` ruleset. Neither takes pull requests into `main` from
  people.
- Agents merging. The owner still merges. No gh command is added to the guard's allow-list.

## Decisions

### D1. Probe first, on a throwaway repository

`tofu/probe` gains `probe_merge_queue` (the ruleset with the `merge_queue` rule) on a public
`troupe-run/infra-probe-merge-queue`, with the infrastructure App and the DCO App installed (memory: install the App
before its ruleset bypass; probe repositories must be public for rulesets). It answers, in order:

1. Does the Free plan offer the queue on an org's public repository? If not, the change stops and goes back to the
   owner.
2. Does a `REBASE` queue land under `required_linear_history`, with `main`'s head equal to the queue's tested commit?
3. Does DCO report on a merge group, from the `dco` App, with sign-offs whose names differ from the GitHub profile
   (dcoapp/app#311)?
4. Does a job skipped by `if:` on `merge_group` report a skipped check that satisfies the queue?
5. Does the App's `always` bypass still push straight to `main`? Can the owner still bypass a failing check, and does
   that skip the queue?
6. Does the queue's push to `gh-readonly-queue/main/...` start `push` workflows? Can anyone create a branch with that
   prefix?

Answers go in this design (a "Probe results" section) before any live change, as earlier probes did.

**Alternative: read the docs and turn it on live.** The docs don't settle 1-3. A wrong guess stalls every merge in a
live repository.

### Probe results (2026-10-27)

On public `troupe-run/infra-probe-merge-queue`, with the module's ruleset and `merge_queue` on, requiring `DCO`
(1861), `probe check` and `probe skipped` (15368, the second skipped by `if:` on merge groups):

1. **The Free plan offers the queue.** GitHub accepted the ruleset with the `merge_queue` rule, and
   `rules/branches/main` lists it with D2's values. (The first apply was refused with "Invalid integration ids"
   until the DCO App was installed on the probe: a check pinned to an App needs that App installed.)
2. **A `REBASE` queue lands under `required_linear_history`.** PRs #2 and #3 landed as `2959b92` and `7432405`, each
   with one parent and each the exact commit the queue's checks ran on. #3 queued on top of #2's group.
3. **DCO reports on merge groups**, from the `dco` App, success on both groups. That includes #3, whose author and
   sign-off are "M. Lau", not the profile's name (dcoapp/app#311 didn't reproduce under rebase).
4. **A job skipped by `if:` reports `skipped` on a merge group, and the queue lands.** D5 holds.
5. **The App's `always` bypass still pushes straight to `main`** (`c7837f4`, signed, recorded as a bypass by
   `troupe-run-infrastructure[bot]`, no queue run). **The owner's `gh pr merge --rebase --admin` merges past a failing
   required check at once, without the queue** (#4, recorded as a bypass). The rollback in the Migration Plan works.
6. **A queue's push to `gh-readonly-queue/main/...` starts `push` workflows**, so guard.yml's exclusion (D3) is
   needed: without it, the guard's push run would fail the queue's commit under `commit-branch-change`. **GitHub
   doesn't reserve the prefix**: a person pushed `gh-readonly-queue/main/pr-99-probe`. D3's exemption keys on the
   `merge_group` event, so that branch's pull request is still judged by the branch rule. Its pushes aren't judged,
   which is no weaker than today: a push to a branch without a pull request reaches nothing protected.

One finding changes how the owner merges: **`gh pr merge` can't add a pull request to the queue here.** With a
queue it asks for auto-merge, and the module sets `allow_auto_merge = false`, so GitHub refuses ("Auto merge is not
allowed for this repository"). GitHub's `enqueuePullRequest` mutation isn't on the guard's gh allow-list. That would leave
`gh pr merge --admin`, which skips the queue entirely, as the only merge that works from a terminal, and an easy wrong
habit. The owner chose (2026-10-27) to turn auto-merge on wherever the queue is on (D2), so `gh pr merge <n>` queues,
the "Merge when ready" button does too, and `--admin` stays the emergency bypass.

### D2. One switch per repository, in the module

The module gets `merge_queue` (bool, default `false`). When it's on, the `protect main` ruleset gains:

```hcl
merge_queue {
  merge_method                      = "REBASE"
  grouping_strategy                 = "ALLGREEN"
  max_entries_to_build              = 5
  max_entries_to_merge              = 5
  min_entries_to_merge              = 1
  min_entries_to_merge_wait_minutes = 0
  check_response_timeout_minutes    = 60
}
```

The same switch sets `allow_auto_merge`, so `gh pr merge` queues rather than failing (Probe results; spec:
repositories). `REBASE` keeps `allowed_merge_methods = ["rebase"]` and the linear history. `ALLGREEN` means each pull request's own
queue commit must pass, so a failure names the pull request that caused it. A wait of 0 lands a lone pull request
straight away. With one maintainer, waiting for a group only adds delay. 60 minutes covers the guard tests on three
OSes with room to spare. `repositories.tf` turns it on per repository. A precondition refuses the switch where
`main_ruleset` isn't `pull-request`.

**Alternative: the queue everywhere at once.** It would stall a repository whose CI doesn't report yet (troupe's and
website's workflows change by their own pull requests, D6), and, if DCO doesn't report, troupe and infrastructure
for good.

### D3. The guard judges a merge group as `main`

`guard.yml` adds `merge_group: types: [checks_requested]` and narrows `push` to `branches: ["**",
"!gh-readonly-queue/**"]`. `github_ci_inputs` reads a `merge_group` event's `merge_group.base_sha` and `head_sha` as
the range, the branch it lands on (`main`, from `base_ref`) and the run's repository, as for a push, with no title or description. Every rule then runs as it does for
a push to `main`. The branch rule doesn't apply to `main`. `openspec_scope` validates in full when the branch is
`main`. Capability labels follow the scope. An event without either commit refuses under `commit-branch-change`,
with the same "re-run, then tell the owner" fix as the other unreadable payloads.

The exemption depends on the event, never on a branch's name. A pull request from a branch someone named
`gh-readonly-queue/...` is still judged by the branch rule (D1.6 checks whether GitHub even allows that name).

**Alternative: exempt queue branches by name on `push`.** If anyone can push such a name, that's a hole in the
branch rule. The event payload comes from GitHub.

### D4. This repository's CI runs on `merge_group`, in full

`ci.yml` adds `merge_group:`. The `changes` job stays `pull_request`-only, so on a merge group `check` and the guard
legs run in full, as on `main` (run-checks-by-path D7: a merged tree may be one no pull request tested). `guard
tests` aggregates as before. The concurrency group already keys on the event and ref, which is unique per queue
entry.

### D5. `plan (pull request)` is skipped in the queue

`tofu.yml` adds `merge_group:` only so the workflow starts and `pr-plan` reports. Its `if:` already needs
`pull_request`, so it reports as skipped, which counts as passed (spec: rulesets). It asks for no approval and holds
no secret. The concurrency group for a merge group is `tofu-mq-<head_sha>`, never `tofu-main`. Otherwise a queue
run would wait behind a plan or apply of `main` that is waiting for the owner's approval, and stall the queue.
`plan (main)`, `oob`, `apply` and `board` keep their `github.ref == 'refs/heads/main'` and event conditions, so
none runs on a merge group.

The owner approved this pull request's plan. What the queue adds is other pull requests' changes, and `plan (main)`
after the merge is made against `main` and approved before anything applies (required-checks D3's reasoning, which
still holds).

**Alternative: plan in the queue too.** It's a second approval on every merge, or a stalled queue if the owner isn't
there. Combined effects are already planned once, on `main`.

### D6. troupe and website change their own CI

Their `check` and `test` workflows aren't delivered files. They change by pull request in their own repositories, by
their own process. This change opens an issue in each, on the roadmap board, saying what to add (`merge_group:`)
and that a path filter or `changes` job must run in full on it. Their queue switches are turned on here only after
those pull requests merge. Their `guard` check arrives by delivery (D3), approved by the owner like any delivery.

### D7. Turning on, in order

1. Probe (D1). If the queue isn't offered or DCO doesn't report, stop: infrastructure and troupe stay off, and #169's
   DCO fallback goes back to the owner as its own decision.
2. One pull request here lands the guard, CI and tofu workflow changes and turns infrastructure's switch on. It is
   the last pull request merged here without the queue. The apply that follows sets the ruleset and delivers the
   guard to troupe and website. infrastructure's own required checks all report on merge groups by then, because
   the workflows on `main` are the ones this pull request brought.
3. The next infrastructure pull request is the live proof. If it stalls, one pull request turns the switch off.
4. website, then troupe, are turned on under a follow-up issue, each after its own CI pull request (D6) merges.

**Alternative: land the workflows first, and turn on infrastructure in a second pull request.** It means a second
issue and change for one line, and proves nothing the probe and step 3 don't.

## Risks / Trade-offs

- [The App's state commit lands on `main` while a pull request is queued] → the queue rebuilds its commit on the new
  `main` and runs again. That costs CI time, never correctness. Deliveries to troupe and website do the same there.
- [A required check renamed in a pull request never reports in the queue] → the same as today on the pull request.
  `test_required_checks.py` gains a test that every required check's workflow in this repository runs on
  `merge_group` when infrastructure's switch is on.
- [Each merge waits for a full CI run, the three-OS guard tests included] → accepted with #169's option 1. The queue
  runs while the owner does other things.
- [The owner bypasses with a failing check and the queue is skipped] → that is the break-glass. It was possible
  before too.
- [DCO flakes in the queue (dcoapp/app#311)] → probed with a sign-off name that differs from the profile. The
  repository's switch can be turned off in one pull request.
- [The queue is stuck, so the pull request turning it off can't land either] → the owner's bypass merges it without
  the queue, or the rule is disabled on GitHub (Migration Plan). D1.5 confirms the bypass before the switch goes on.
- [Turning the queue off while pull requests are queued] → GitHub removes them from the queue. They are merged again
  by hand. Nothing is lost.

## Migration Plan

D7 is the rollout. Rollback is the switch: `merge_queue = false` for a repository, applied after the owner approves
its plan. The `merge_group` triggers can stay, since nothing sends them.

A stuck queue holds the switch-off pull request too, so the rollback starts outside it: the owner merges that pull
request with their bypass, merging without the queue (D1.5 shows this works before anything goes live), or, failing
that, disables the merge queue rule on GitHub, which the next plan shows as drift until the switch-off applies.

## Open Questions

None that change the plan. The probe's answers (D1) decide how far step D7 goes, and a negative answer on 1 or 3 is
taken back to the owner rather than worked around.
