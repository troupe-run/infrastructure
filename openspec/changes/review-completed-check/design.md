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
`if: always() && github.event_name != 'merge_group'`. `always()` makes it run whatever happened before it, including
a cancelled review, so it reports a failure rather than leaving nothing. It sits outside the concurrency group, so a
newer run's review never cancels it; it doesn't need cancelling, because it does nothing but decide.

The name says what it checks and can't be confused with the review job (`claude review`). It's unique across the
three repositories' workflows.

**Alternative: a commit status written by the review job.** Commit statuses are documented as latest-write-wins per
context, and the job would write it to the head explicitly, settling D1's first question. But a fork's run has a
read-only token and couldn't write it, so a fork's pull request could never merge, which #242 rules out. The owner
also chose a job (#242).

### D3. What the job decides, in order

Its step reads the needs' results and the event, never anything the pull request controls in an expression:

1. **Not reviewed by design** (the pull request's author is a bot, or it's from a fork; the same test as the gate's
   `if:`): pass, saying why. This covers Dependabot, release-please (`troupe-run-release[bot]`), any App's and a
   fork's pull request.
2. **This run reviewed** (`gate` succeeded with `review=true`): pass if `review` and `resolve` both succeeded.
   Otherwise fail, naming each that didn't and `gh run rerun <run id>` with this run's ID. `resolve` counts because a
   review whose must-fixes weren't resolved leaves the pull request's state undecided, and re-running is cheap.
3. **The gate failed or was cancelled**: fail, naming the run to re-run. Whether the event needed a review isn't
   known, so the conservative answer is "not completed".
4. **This run reviews nothing by its event** (`gate` skipped by its `if:` for a comment, or `gate` said `review=false`):
   carry forward (D4).

Every failure is an `::error` annotation whose title is short and whose message has the command to run.

### D4. Carrying forward the latest review of the head

In a run that reviews nothing, the job asks the Actions API (with `actions: read`, the run's own token) for this
workflow's runs on the pull request's head, newest first, skipping this run, and takes the first whose `claude review`
job wasn't skipped. Then:

- that run's `claude review` and `resolve review conversations` jobs both succeeded → pass, naming the run;
- it was cancelled or failed → fail, naming that run for `gh run rerun`;
- it's still queued or running → fail, saying a review is running and its own check reports when it's done;
- none is found, or the API can't be read → fail, saying so and suggesting a push or re-running the last review run.

Which runs count as "on the head" depends on D1's first answer:

- **If a reply's run reports on the head**, the API query is by `head_sha` (the pull request's head from the event),
  and a reply's review run counts like a push's. This is the case #242 expects.
- **If it doesn't**, a reply's run, and its checks, never touch the head's required check. Then a reply's review
  can't turn a cancelled push review green, so the only way past a cancelled push review is to re-run it, which the
  check's message says. The job still runs in reply runs (it's harmless off the head) but needn't carry forward; the
  design then drops step 4 to a plain pass and records why.

The "still running" case relies on D1's second answer: the running review's own `claude review completed` must count
once it reports. If the ruleset counts the check run created last, and the running run's check run was created
earlier, the reply run's failure would stick. Then step 4 instead waits for that run (polling, bounded by the job's
timeout) rather than failing at once.

**Alternative: skip the job in runs that review nothing.** A skipped required check counts as passed, and could be the
latest check on the head. That's exactly the hole this change closes.

### D5. `merge_group:` and the queue

`claude-review.yml` adds `merge_group:` to its triggers only so `claude review completed` reports, as skipped, on
each group's commit (merge-queue design D5's pattern for `plan (pull request)`). On a merge group the gate's `if:` is
false (there's no pull request), so `gate`, `review` and `resolve` are skipped too, and nothing is minted or spent.
The concurrency group names a pull request number; skipped jobs never join it.

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
secrets, no checkout) the way it pins the others, and runs the job's script with stubbed `gh` answers for each case in
D3 and D4, named for what each checks. The required-checks tests already fail when a required name has no job; they
gain the new name for all three repositories. A docs test checks `docs/development-workflow.md` names the check.

## Risks / Trade-offs

- [An expired Claude token blocks every member's pull request in three repositories] → the run fails loudly, the
  check names the re-run, and the owner can bypass with `gh pr merge --admin` in an emergency. Renewing the token is
  already in `oob/README.md`.
- [A run that reviews nothing fails while an earlier review is still running, and stays the latest] → D1 tests it;
  D4 waits instead if so.
- [The Actions API's runs list is paginated and filtered by `head_sha`] → the query asks for this workflow only and
  pages until it finds a run whose review wasn't skipped; the review's own comments can add many runs to one head.
- [GitHub caps a run's job outputs or changes a job's check run name] → the tests pin the name; the after-merge check
  is a real pull request seen blocked and unblocked.
- [Extra runs: every bot comment's run now runs a short job] → it mints nothing and makes one or two API reads.

## Migration Plan

1. Probe (D1); record results here; delete the probe repository.
2. Build the job, the trigger, the tests and the docs; CI green on all three OSes, troupe's and website's checks run
   against the new file (the file's header says how).
3. After merge, the owner approves the plan: delivery to troupe and website, and the three rulesets.
4. Check on a real pull request that the check reports, and comment on the open pull requests that need a push.

**Rollback:** remove the name from `tofu/required-checks.json` and apply. The job can stay; unrequired, it's
harmless.

## Probe results

To be filled in by task 1.
