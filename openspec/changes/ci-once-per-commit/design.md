# Design

## Context

See proposal.md for why. What the change works with:

- `ci.yml`'s `changes` job runs only on `pull_request`. It answers `scope` and `check-args` (from `guard.py
  check-scope`) and `guard` (from `guard_tests_needed.py`). `check` runs unless `scope == 'none'`; the legs run
  unless `changes` succeeded and said `guard=false`; `guard tests` passes when the legs passed, or were skipped
  because `changes` succeeded with `guard=false` (run-checks-by-path design D6, D7). A push to `main` or a merge group
  has no `changes`, so everything runs.
- `tofu.yml`'s `plan (main)` starts on CI's `workflow_run` with `conclusion == 'success'`. A run whose jobs are
  skipped concludes `success`, as on any docs-only pull request today. `scripts/main_ci.py` (daily and manual plans)
  reads the push run's conclusion, not its jobs, and so does nothing that delivers the guard.
- Measured 2026-10-30 on 4a64b25: CI's `merge_group` run concluded success at 01:00, the `push` run on the same SHA
  ran the full matrix again from 01:10, and `tofu`'s `workflow_run` started at 01:20. So the commit the queue passes
  is the one that lands on `main`, as #227 measured in troupe.
- `claude-review.yml` triggers on `opened, synchronize, reopened, ready_for_review`, and is delivered with the guard
  to troupe and website.
- The guard lists `("pr", "create")` and `("pr", "ready")` in `GH_WORKFLOW_WRITES` and grants both; `--draft` is one
  of `gh pr create`'s value-less flags it already reads.

## Goals / Non-Goals

**Goals:**
- One full run of the legs per commit that lands through the queue, with CI's run on `main` still green so the plan
  and apply chain is unchanged.
- No legs and no plan approval on a draft; both on `ready_for_review`.

**Non-Goals:**
- troupe's and website's `ci.yml` (troupe-run/troupe#204, troupe-run/website#77), and troupe's D1 caveat about a
  draft's `check`. This repository's `changes` doesn't narrow by a previous head, so the caveat doesn't arise here.
- A guard rule that refuses `gh pr ready` while findings are open. #227 rejected it.
- The `guard` check's triggers. It's cheap, and a required check that must report on drafts too.

## Decisions

### D1. Ask for CI's merge-queue run on the commit, not a `check` check-run

On a push to `main`, the question is "did CI's `merge_group` run on `github.sha` succeed?":
`gh run list --workflow ci.yml --commit <sha> --event merge_group --json status,conclusion`. Any completed run that
succeeded counts. A re-run of the same commit tested the same tree.

The issue's wording was "a successful `check` from GitHub Actions on `github.sha`". A check-run named `check` can come
from a pull request's run, where it may be scoped or skipped and the legs may not have run. The queue's run is the
only one that always ran everything, so the lookup names its event. *Alternative:* the check-runs API filtered by
name. Rejected: it can't tell a merge-group suite from a pull request's without a second read per suite.

### D2. `changes` decides every case, through the answers it already gives

`changes` runs on `pull_request` and `push` (`github.event_name != 'merge_group'`). It answers in its existing
outputs:

| Event | Answer |
| --- | --- |
| merge group | no `changes`: everything, as today |
| push, queue passed the commit | `scope=none`, `check-args=` (empty), `guard=false` |
| push, anything else | `scope=full`, `check-args=` (empty), `guard=true` |
| pull request, draft | `scope=none`, `check-args=` (empty), `guard=false` |
| pull request, ready | the changed paths' answers, as today |

So `check`'s and the legs' conditions, `guard tests`' judgment (`guard_tests_needed.py --result`), and the skip path
proven in run-checks-by-path all stay as they are. Each skip is the case they already handle: `changes` succeeded
and said nothing is needed. *Alternative:* add `github.event.pull_request.draft != true` and a queue condition to each
job's `if`. Rejected: four places to keep in step, and `guard tests` would need a new "skipped on purpose" state.
That's the kind of skip nobody asked for that D6 exists to fail.

`tofu.yml`'s `changes` does the same for the plan: `plan=false` on a draft, so `plan (pull request)` is skipped and
asks for no approval. Its condition is unchanged. A failed `changes` still plans, in both workflows: failing safe
costs runs or an approval, never a missing check.

Both workflows add `ready_for_review` to their `pull_request` types. GitHub's default types (opened, synchronize,
reopened) are written out with it, since naming any type replaces the default list. The event's payload carries
`draft: false`, so the ready run is an ordinary one.

### D3. A failed read never turns `main` red

On a push, a failed `changes` job would make CI's run conclude `failure`. Then `tofu.yml`'s `workflow_run` doesn't
plan, and a read error would hold up the apply. So the lookup never fails the job. A read that fails, an answer it
can't parse, or a status it doesn't know all answer "full", with a `::warning::` naming why, and exit 0. The tests
then decide the run's result, as today.

The queue lands a commit only once its required checks pass, so its run has normally completed when the push run
asks. A run still `queued` or `in_progress` (jobs done, run not yet closed) is polled every 10 seconds for up to 2
minutes, then answers "full". That's the same bounded-wait shape as `main_ci.py`.

### D4. One standard-library script for the lookup

`scripts/queue_passed.py --repository <owner/repo> --sha <sha>` prints the three output lines for `$GITHUB_OUTPUT`,
following `main_ci.py`'s pattern: standard library, git and gh only, runnable with the runner's `python3` before uv,
and a `gh` callable injected for tests. `changes` gets `actions: read` for it, on top of `contents: read`. The draft
answer is a three-line step in each workflow, reading `github.event.pull_request.draft` through `env`. It has no
logic worth a script, and the workflow tests pin it.

### D5. Marking ready doesn't start a review

`claude-review.yml` drops `ready_for_review` (owner, 2026-10-30). Opening, reopening and every push still start one,
so a draft's head is always reviewed before it's marked ready. A push after ready is reviewed as before. The one
loss: if a draft's last review run failed, marking it ready no longer retries it. Re-run it (`gh run rerun <id>`), as
the docs already say. The file is delivered with the guard, so this pull request's plan shows its delivery to troupe
and website.

### D6. The step is documented, in the places agents read

- `docs/development-workflow.md`, "Claude's review": a pull request opens as a draft (`gh pr create --draft`); the
  review's findings are acted on; once the review of its last push has nothing left to fix, `gh pr ready <n>`. Why:
  CI's legs and the plan wait for ready, and marking ready early only costs runs.
- `CLAUDE.md`, steps 4 and 5 of "How work happens here".
- `org-profile/CONTRIBUTING.md`, steps 3 and 4. It's the full guide CLAUDE.md points to, for every governed
  repository, so the step belongs there even before troupe and website change their CI. A draft there still runs CI
  as today, so following the step costs nothing in the meantime.

The header comments of `ci.yml` (its D7 sentence, "main runs everything after every merge") and `tofu.yml` (its
trigger table) are updated, since each states what its triggers do.

## Risks / Trade-offs

- [The queue's commit differs from the one that lands, for example if GitHub's merge method changes] → No
  `merge_group` run exists on the landed SHA, so it runs everything. The risk only costs time, never a skipped test.
- [A flake that the duplicate run used to catch by accident is no longer seen] → Accepted in #227. Flake hunting is
  done on purpose (troupe-run/troupe#168).
- [An agent marks ready before the review is clean] → Costs a run of the legs and a plan approval. A draft can't
  merge, and the ruleset blocks a merge with unresolved conversations.
- [A draft's required checks read as passed] → A draft can't be merged or queued, and `ready_for_review` runs them
  again. The draft step's notice says why they were skipped.
- [The ready run is a few minutes behind the review when the first review is clean] → Accepted in #227. It saves the
  most when the review has findings, which has been most pull requests so far.

## Migration Plan

This change's own pull request is the live check. Each case's own workflow file runs it: `pull_request` and
`push` runs read the files on the pull request's branch and on `main`.

1. Open it as a draft: CI's legs and `check` skipped, `guard tests` green, no plan approval asked.
2. Once the review is clean, mark it ready: the legs run, the plan asks for approval, and no review starts.
3. After the queue merges it: CI's push run on `main` skips its legs and succeeds, and `plan (main)` starts.

Rollback is a revert through the same path. With no `changes` on a push, everything runs again.

troupe and website pick up the review trigger with this plan's delivery, and their own CI with #204 and #77.
