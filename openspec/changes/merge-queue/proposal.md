# Proposal

## Why

The rulesets don't require a pull request to be up to date with `main` before it merges (required-checks design D3),
so two pull requests can each pass and still break `main` together. Only CI's run on `main` catches that, after the
merge. Issue #169 weighs the fixes. The owner leaned towards a merge queue in every governed repository rather than
strict up-to-date checks, and this change builds that option (1 in #169). A queue tests each pull request on top of
`main` and whatever is queued ahead of it, then lands exactly what it tested. The owner's merge click stays the one
manual step.

## What Changes

- **A throwaway probe first** (`troupe-run/infra-probe-*`), for what GitHub's docs don't settle: that the Free plan
  offers a queue on an org's public repository, that a rebase queue satisfies `required_linear_history`, that the DCO
  App reports on merge groups, that a job skipped by `if:` reports as skipped on a merge group, that the App's
  `always` bypass still pushes straight to `main`, that the owner's pull-request bypass still merges past a failing
  check, and whether a push to the queue's `gh-readonly-queue/main/...` branch starts `push` workflows. Every later
  step depends on these answers.
- **The `main` ruleset gains a `merge_queue` rule**, merging by rebase, behind a per-repository switch in the
  repository module, so each repository is turned on only once every check it requires reports on merge groups.
  Strict up-to-date checks stay off: the queue does what strict would, without making every open pull request
  stale after each state commit or delivery.
- **The guard runs on `merge_group`** and judges a queue's range as it judges `main`: commit messages, schema
  commit types, archived tasks, delivered files, strict OpenSpec validation in full and capability labels. No branch
  rule and no description rule, since every pull request in the group already passed them. Its `push` trigger leaves
  queue branches out, so a queue branch is never judged as a branch with no change. This is a guard file, so it
  reaches troupe and website by delivery.
- **This repository's CI runs on `merge_group`, in full** (`check` and every `guard tests` leg), like a push to
  `main`.
- **`plan (pull request)` is skipped on a merge group.** It's required, and its run waits for the owner's approval
  of `plan-pr`, so running it in the queue would mean a second approval for every merge, or a stalled queue. The
  owner already approved the pull request's plan, and `plan (main)` after the merge is still planned against `main`
  and approved before anything applies. The `tofu` workflow gets the `merge_group` trigger only so the skipped job
  reports, in a concurrency group of its own, never `main`'s.
- **troupe's and website's own CI workflows** (`check`, `test`) need `merge_group` too. Those files are theirs, so
  they change by pull request in those repositories, under issues this change opens. A repository's queue is turned
  on only after that lands.
- **This change turns on infrastructure's queue only.** Its own checks report on merge groups once this change
  merges. website and troupe follow under an issue of their own.
- **The merge step in the docs** (CLAUDE.md, the org's CONTRIBUTING.md, `docs/standard-changes.md`) becomes "add to
  the merge queue".

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `rulesets`: pull requests into `main` reach it through a merge queue that merges by rebase and needs every
  required check to pass on the queued combination, in each repository whose switch is on.
- `ci-apply`: CI tests the queue's combination in full, and the pull request's plan isn't run again in the queue.
- `development-workflow`: the guard re-checks a merge group as it does `main`, and a queue's branch push isn't judged
  as a branch with no change.

## Impact

- `tofu/modules/repository/` (the `merge_queue` rule and its switch), `tofu/repositories.tf` (which repositories
  are on), `tofu/probe/`.
- `.github/workflows/guard.yml` and `scripts/guard.py` (delivered to troupe and website), `.github/workflows/ci.yml`,
  `.github/workflows/tofu.yml`, and their tests under `scripts/tests/`.
- troupe and website: a pull request each, adding `merge_group` to their CI, before their queues are turned on.
- CLAUDE.md, `org-profile/CONTRIBUTING.md` (published to `troupe-run/.github`), `docs/standard-changes.md`,
  `docs/development-workflow.md`.
- Every merge waits for one CI run on the queue, including the guard tests on three OSes in this repository.
- **DCO:** troupe and infrastructure both require it. The DCO App has supported merge groups since July 2026
  (dcoapp/app#292, #303), and its installation here already holds `merge_queues: read`. If the probe shows it
  doesn't report, those two repositories keep their switch off, and #169's fallback (a DCO check of our own, or not
  requiring DCO in the queue) goes back to the owner. Note that #169's option 4 named infrastructure as a
  queue-first repository, but infrastructure also requires DCO. Only website doesn't.
