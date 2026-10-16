# Design: CI tests a pull request once, and main after each merge

## Context

See proposal.md for why. What shapes the approach:

- `ci.yml` runs on `pull_request` and on `push: branches: ["**"]`. Its concurrency group is
  `ci-${{ github.event_name }}-${{ github.ref }}`, so the two runs never cancel each other.
- `tofu.yml`'s plan of `main` starts on `workflow_run` for the workflow named `CI`, branch `main`, when it concludes
  `success`. Then it waits for `guard.yml`'s **push** run on the same commit (`gh run list ... --event push`). The
  README's delivery steps rely on that order: "plans the delivery only after CI is green on all three OSes".
- The required checks (`tofu/required-checks.json`) are the jobs a pull request reports.
  `test_infrastructure_requires_exactly_its_pull_request_jobs` derives them from each workflow's `pull_request` jobs,
  so the `push` trigger doesn't enter into it. A `pull_request` run's check runs report on the pull request's head
  commit, which is where the ruleset looks for them.
- For a `pull_request` event, GitHub runs the workflow file as it is in the pull request's merge commit. For a
  `push`, it runs the file in the pushed commit. So this change's own pull request already runs with the narrowed
  trigger, and its head commit shows the effect.
- `guard.yml`'s triggers are pinned by `test_guard_re_runs_when_a_pull_request_is_renamed_and_still_runs_on_every_push`.
  `ci.yml`'s aren't pinned anywhere.
- troupe's `ci.yml` already uses `pull_request` plus `push: branches: [main]`.

## Goals / Non-Goals

**Goals:**
- Each CI job reports once per pull request update, and `main` is still tested, then planned, after every merge.
- The App's state commit after an apply doesn't run CI again.
- A test fails if `ci.yml` stops running on `main`'s pushes, since the plan of `main` would then never start.

**Non-Goals:**
- `guard.yml`'s triggers. The owner decided on 2026-10-16 to leave them as they are (proposal, out of scope).
- `tofu.yml`, the required checks, or the rulesets.

## Decisions

### D1. Narrow `push` to `main`, and keep `pull_request` as it is

`on: pull_request` plus `push: branches: [main]`, the shape troupe's `ci.yml` already has. The `pull_request` run
tests the branch merged onto `main`, which is what will land. The `push` run on `main` tests what did land, and it's
what `tofu.yml`'s `workflow_run` follows.

Alternatives considered:
- **Keep `push` on every branch and drop `pull_request`.** The checks would still report on the head commit, but they
  would test the branch's head without `main`, and the required-checks test (which reads `pull_request` jobs) would
  need rewriting. Rejected.
- **Keep both, and skip the `push` run's jobs when the branch has an open pull request.** A job can't know that from
  the event without an API call, and the skipped jobs still report as check runs. Rejected: more moving parts for
  the same result.
- **Share one concurrency group across both events, so one cancels the other.** It cancels whichever run started
  first. That can be the `pull_request` run, and its cancelled required checks would block the merge. Rejected.

### D2. Ignore a push to `main` that changes only the state file

`push: branches: [main]` with `paths-ignore: [tofu/terraform.tfstate]`. GitHub skips the workflow when every path a
push changes matches `paths-ignore`. The App's state commit changes only that file, and the App pushes it on its own,
so its run doesn't start. A merge's push changes other files too, so it still runs. A `pull_request` run has no path
filter, so the required checks report on every pull request, even one that touches only the state file.

The CI run on the state commit has no consumer. The plan that follows it, in `tofu.yml`, already ends at "Skip the
App's own state commit". The daily and manual plans run on `schedule` and `workflow_dispatch`, not after CI.
`tofu.yml`'s skip step stays. It also covers a state commit that reaches `main` some other way, and removing it
isn't needed for this change.

Alternatives considered:
- **An `if:` on each job that checks the author and the changed files.** The jobs still report as skipped check runs,
  the workflow_run still fires, and the same test is repeated in two workflows. Rejected.
- **A lighter matrix on `main` (only `check`).** It would drop the "green on all three OSes" a delivery waits for.
  Rejected: the merged commit's run is the one that must stay whole (proposal, out of scope).

### D3. Pin the triggers with tests, and tie them to `tofu.yml`

Two tests, next to the guard's trigger test in `scripts/tests/test_required_checks.py`:

- `ci.yml` runs on `pull_request` with no path filter, and on `push` to `main` only, ignoring exactly
  `tofu/terraform.tfstate`. That's the path `tofu.yml`'s skip step reads as the App's state commit, and the test
  checks that `tofu.yml` names it, so a renamed state file breaks the test rather than the filter.
- Every branch that `tofu.yml`'s `workflow_run` follows is a branch `ci.yml` runs on for pushes, and the workflow it
  names is `ci.yml`'s `name`. This is the dependency that would break silently: if the trigger drifted off `main`,
  or `CI` were renamed, `main` would never be planned again, and nothing would fail.

The comment at the top of `ci.yml` says when it runs and why, and points to #66.

### D4. Leave the concurrency group alone

`ci-<event>-<ref>` still gives a pull request (`refs/pull/<n>/merge`) and `main` (`refs/heads/main`) their own
groups. Each new push to a pull request still cancels that pull request's previous run.

## Risks / Trade-offs

- [A pull request with a merge conflict gets no CI run: GitHub can't build its merge commit, so `pull_request`
  workflows don't start] → it can't merge anyway until it's rebased. Every commit has passed
  `scripts/check.py` locally (development-workflow, "Checks pass before a commit"), and `guard` still runs on the
  push.
- [A branch pushed without a pull request isn't tested on GitHub's runners, so Windows or macOS breakage shows only
  once a pull request is open] → every change reaches `main` through a pull request, and its required checks run
  there before merge. Opening a draft pull request gets them early.
- [A break-glass apply's state reaches `main` through a pull request that changes only the state file (README,
  "Break-glass"), so its merge doesn't run CI and isn't planned straight after] → that pull request's own CI and plan
  still run. The state then matches the org, so a plan would show nothing, and the daily plan runs on it within a
  day. The owner can also start a run by hand.
- [A Dependabot pull request's CI now comes only from its `pull_request` run] → CI needs no secret, so its read-only
  token is enough, and that run is the one the ruleset already reads.

## Migration Plan

Merging is the migration. The first pull request after it, this change's own included, reports each CI job once.
This change's merge is the first push the new `push` trigger sees. If its apply commits state (it shouldn't: the plan
should show no changes), that commit is the first one CI skips. Otherwise the next applied merge shows it.
Rollback is reverting the commit. Nothing is applied to the org: OpenTofu reads neither `ci.yml` nor the test file.
`scripts/plan_needed.py` doesn't list `.github/workflows/`, so the pull request is still planned, and that plan and
`main`'s after the merge should both show no changes. Adding `ci.yml` to `plan_needed.py`'s list is left alone: a
path left off the list costs one approval, and the list is kept short on purpose.
