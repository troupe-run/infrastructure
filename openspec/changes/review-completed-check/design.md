# Design

## Context

See proposal.md for why. What shapes the approach:

- `claude-review.yml` has three jobs: `gate` (decides whether the event needs a review; its own `if:` skips bots',
  forks' and non-reply events outright), `review` (Claude; job-level concurrency group `claude-review-<number>`,
  `cancel-in-progress: true`) and `resolve` (same group; resolves the review's must-fixes). It runs on
  `pull_request` (opened, synchronize, reopened) and `pull_request_review_comment` (created).
- **Every** run of the workflow reports a check run for each of its jobs, skipped ones included. The review's own
  inline comments each start a run whose jobs are all skipped. A required check that's skipped counts as passed
  (spec: rulesets), so a job that's merely skipped in those runs would be a pass, and could be the latest one.
- The file is delivered to troupe and website (`tofu/guard_delivery.tf`), whose required checks are in
  `tofu/required-checks.json` with infrastructure's. All three merge through a queue: a required check must report
  on `merge_group` or the queue waits (merge-queue design D5).
- Fork runs get no secrets and a read-only token.

## Goals / Non-Goals

**Goals:**
- A required check that's green on a head only when a review of that head completed, or when the pull request isn't
  reviewed by design.
- No run of the workflow, whatever its event, can turn a cancelled or failed review green by reporting after it.

**Non-Goals:**
- Making the review job itself required, or changing what the review checks or how it tiers findings.
- A guard rule at `gh pr ready`. The issue allows one on top later; the check covers agents and people alike.
- Re-running a cancelled review automatically. The check says how; a person or agent does it.

## Decisions

### D1. Probe first: which commit a reply's run reports on, and which check counts

Two GitHub behaviours decide the shape of D4 and aren't documented clearly enough to build on:

1. For a `pull_request_review_comment` run, is the workflow run's `head_sha`, and so the commit its jobs' check runs
   land on, the pull request's head? (Its `GITHUB_SHA` is the merge ref's commit.)
2. When a commit has two check runs of the same name from the same App, does the branch ruleset count the one
   created last, or the one completed last? In particular: a check run created early as queued/pending in one run,
   then a later run's failed check run, then the first one completing as success.

Probe on `troupe-run/infra-probe-review-check` (public, a copy of the workflow with a stub in place of Claude: a step
that sleeps or exits 1 on demand, and no secrets), with a ruleset requiring the check. Record the answers in
"Probe results" here before D4's code is written. The guard allows an agent to create, configure and delete
`infra-probe-*` repositories (#217).

### D2. One job at the end, named `claude review completed`

A fourth job, `completed`, named `claude review completed`, `needs: [gate, review, resolve]`, with
`if: always() && github.event_name == 'pull_request'`. `always()` makes it run whatever happened before it, including
a cancelled review, so it reports a failure rather than leaving nothing. It sits outside the concurrency group, so a
newer run's review never cancels it; it doesn't need cancelling, because it does nothing but decide.

The name says what it checks and can't be confused with the review job (`claude review`). It's unique across the
three repositories' workflows.

**Alternative: a commit status written by the review job.** Commit statuses are documented as latest-write-wins per
context, and the job would write it to the head explicitly, settling D1's first question. But a fork's run has a
read-only token and couldn't write it, so a fork's pull request could never merge, which #242 rules out. The owner
also chose a job (#242).

### D3. What the job decides, in order

The job runs only on `pull_request` events (D4). Its step reads the needs' results and the event from `env:`, never
from an expression in the script:

1. **Not reviewed by design** (the pull request's author is a bot, or it's from a fork; the same test as the gate's
   `if:`): pass, saying why. This covers Dependabot, release-please (`troupe-run-release[bot]`), any App's and a
   fork's pull request.
2. **This run reviewed** (`gate` succeeded with `review=true`, which it always says for a pull request event): pass
   if `review` and `resolve` both succeeded. Otherwise fail, naming each that didn't, with `gh run rerun <run id>`
   for this run. `resolve` counts because a review whose must-fixes weren't resolved leaves the pull request's state
   undecided, and re-running is cheap.
3. **Anything else** (the gate failed, was cancelled, or gave no answer or another one): fail, naming the run to
   re-run. Whether the head was reviewed isn't known, so the safe answer is "not completed".

Every failure is an `::error` annotation whose title is short and whose message has the command to run.

### D4. Only a pull request event's run reports the check

The probe (Probe results 1 and 2) showed that a comment's run lands its check runs on the pull request's head, and
GitHub links its check suite to the pull request, but the pull request's checks and its ruleset ignore it: they read
only the newest `pull_request` run on the head. So nothing a comment's run reports can turn a cancelled review green,
or a completed one red.

The job's `if:` is therefore `always() && github.event_name == 'pull_request'`: skipped on a comment's run, and on a
merge group (D5). Carrying the latest review forward in a comment's run, as this design first planned, would
compute an answer nothing reads.

What that means for a reply: a reply to a must-fix that cancels a push's review still running leaves the push run's
check failed, and the reply's own review, though it completes, doesn't count. The way past is to re-run the push's
run, which the check's message names. That review reads the conversations afresh, so it judges the reply too. It
costs one more review than #242 expected, in the case where a reply arrives while a push's review runs.

**Alternative: carry forward in comment runs anyway**, in case GitHub starts counting them. It's an API read on every
one of the review's own comments, to guard against a change nobody has announced; the after-merge check on a real
pull request is where a change would show.

**Alternative: a reply's run waits for a running review instead of cancelling it** (`cancel-in-progress` true only
for `pull_request`). It would spare the re-run, but it changes the review's concurrency design (review-judge-reply-on
-post D3) and has edge cases of its own, since a group holds one pending run. That's a separate decision for the owner,
outside #242.

### D5. `merge_group:` and the queue

`claude-review.yml` adds `merge_group:` to its triggers only so `claude review completed` reports, as skipped, on
each group's commit (merge-queue design D5's pattern for `plan (pull request)`). On a merge group the gate's `if:` is
false (there's no pull request), so `gate`, `review` and `resolve` are skipped too, and nothing is minted or spent.
The concurrency group names a pull request number; skipped jobs never join it. The probe's queue landed its pull
request with the check skipped on the group's commit (Probe results 4).

### D6. Required in all three repositories, in one apply

`tofu/required-checks.json` adds `{"context": "claude review completed", "app": "github-actions"}` to troupe,
infrastructure and website. The delivery of the new workflow and the ruleset change go out in the same apply after
merge; within it the rulesets apply first (`guard_delivery.tf` depends on the repository modules), so for a moment
troupe and website require a check their `main` doesn't run yet. Nothing can merge in that moment, since every open
pull request also lacks the check until its next run.

An open pull request picks the workflow up from its merge commit with base on the next push (a `pull_request` run
uses the merge ref's workflow files), and only then reports the check. Until then it can't merge. That's the same as
a new required check has always been; the after-merge comment lists the open pull requests that need a push.

**Alternative: deliver first, require in a second change.** It avoids the moment above, but costs a second change and
approval for a window that blocks nothing in practice.

### D7. Tests

`scripts/tests/test_claude_review_workflow.py` pins the new job (name, needs, `if:`, permissions, timeout, no
secrets, no checkout, no concurrency group) the way it pins the others, and runs the job's script for each case in
D3, named for what each checks. The required-checks tests already fail when a required name has no job; they
gain the new name for all three repositories. A docs test checks `docs/development-workflow.md` names the check.

## Risks / Trade-offs

- [An expired Claude token blocks every member's pull request in three repositories] → the run fails loudly, the
  check names the re-run, and the owner can bypass with `gh pr merge --admin` in an emergency. Renewing the token is
  already in `oob/README.md`.
- [GitHub starts counting a comment run's checks for the pull request] → a comment's run would then report a skipped
  check, which counts as passed. Nothing announced suggests it; the probe's reads are recorded below, to repeat if
  the check ever passes where it shouldn't.
- [A reply that cancels a push's running review costs a re-run] → the check names it; the alternative in D4 is the
  owner's to choose.
- [GitHub caps a run's job outputs or changes a job's check run name] → the tests pin the name; the after-merge check
  is a real pull request seen blocked and unblocked.

## Migration Plan

1. Probe (D1); record results here; delete the probe repository.
2. Build the job, the trigger, the tests and the docs; CI green on all three OSes, troupe's and website's checks run
   against the new file (the file's header says how).
3. After merge, the owner approves the plan: delivery to troupe and website, and the three rulesets.
4. Check on a real pull request that the check reports, and comment on the open pull requests that need a push.

**Rollback:** remove the name from `tofu/required-checks.json` and apply. The job can stay; unrequired, it's
harmless.

## Probe results

Run on `troupe-run/infra-probe-review-check` (2026-11-01), with a copy of the workflow whose review is a stub and a
ruleset requiring `claude review completed` from `github-actions`. Pull request #1, head `50d7ce1`.

1. **A comment's run reports on the head, and is linked to the pull request.** The reply's run (41258230382, event
   `pull_request_review_comment`) has `head_sha` `50d7ce1`, the head; its check runs are among the head's check runs,
   and its check suite lists the pull request. Its `GITHUB_SHA` is the merge ref's commit.
2. **The pull request counts only its newest `pull_request` run.** The push's run (41258217217) had its review
   cancelled by the reply's run and reported `claude review completed` failed at 00:48:16; the reply's run reported
   it passed at 00:50:31. The pull request stayed `BLOCKED`, and `statusCheckRollup` and `gh pr checks` listed only the
   push run's jobs. Then two reopens on the same head: run A (41258596608), and run B (41258659793) 50 seconds later,
   which cancelled A's review. A's check failed after B had started; when B's passed, the pull request was `CLEAN`,
   with both failures still listed. And as soon as run C (41258918187) was created, before it had reported anything,
   the pull request went `BLOCKED` though B's success was listed: the newest run decides, and a check it hasn't
   reported yet is missing.
3. **A cancelled run still reports a failure, and a re-run counts.** `gh run cancel` on run C cancelled its review
   and resolving jobs, but the `always()` job ran and failed: `BLOCKED`, with B's success listed. `gh run rerun` gave
   attempt 2, whose check passed: `CLEAN`.
4. **The merge queue lands with the check skipped.** With `merge_group:` added, a `merge_queue` rule on the ruleset
   and auto-merge on, `gh pr merge 1 --rebase` queued the pull request. The group's run (41259300771) skipped every
   job, `claude review completed` among them, on the group's commit `9681caa`, and the queue landed it on `main`.

The probe repository was deleted afterwards.
