# Design

## Context

See proposal.md for why. What shapes the approach (read 2026-10-26):

- **Which commit a run plans.** `plan (main)` sets `sha` to `github.event.workflow_run.head_sha`, or `GITHUB_SHA`
  for a scheduled or manual run, and checks it out with `fetch-depth: 2`. The state is a file in the checkout
  (`tofu/terraform.tfstate`), so the plan reads that commit's state, however old.
- **Who writes state.** Only an apply: CI's, as the App, through `commit_state.py`, in a commit that changes only the
  state file; or a break-glass local apply, through a pull request. CI's runs on `main` share one concurrency group,
  so no state commit lands while a plan of `main` is running, except by break-glass.
- **The state commit.** `commit_state.py` writes it on the blob the plan read, so it 409s when `main`'s state moved,
  and its message names the commit applied. CI doesn't test it (`paths-ignore`), so it never gets a `workflow_run` of
  its own. The guard still runs on its push.
- **The existing skip.** "Skip the App's own state commit" skips a `workflow_run` whose commit is a state commit
  (author is the App's bot and the only file is the state). `test_required_checks.py` finds it by name and checks it
  reads the same path CI ignores.
- **Apply and state commit** use `needs.plan.outputs.sha` for their checkout and for `--planned`, so whatever the plan
  job names flows through.
- **GitHub's event fields.** For `workflow_run` and `schedule`, `GITHUB_SHA` is the default branch's head when the
  event fired, not when the job starts. A run queued in the concurrency group starts later.

## Goals / Non-Goals

**Goals:**
- One rule decides the commit to plan, in one place, tested against real repositories.
- No plan of `main` reads a state older than `main`'s.

**Non-Goals:**
- Waiting for CI in a scheduled or manual run (#167's second route): see Open Questions.
- The `drift (out of band)` job. It checks GitHub against `oob/`, and reads no state, so a stale commit can't make it
  re-apply anything.
- Break-glass applies. They change state through a pull request, which is a merge like any other here.

## Decisions

### D1. The rule: plan with the current state, or plan nothing

`scripts/plan_target.py` decides, given the event, the run's commit C and `main`'s head H as fetched when the job
starts:

For a `workflow_run`, the commits with C's declaration are C and the unbroken run of state commits straight after it
on `main`. Call the last of them P. A state commit changes only the state, so P's declaration is C's, with the newest
state any of them has.

| Event | Case | Plans |
|---|---|---|
| `schedule`, `workflow_dispatch` | always | H |
| `workflow_run` | C is a state commit | nothing (as today) |
| | C isn't an ancestor of H | fails, naming C |
| | P's state blob is H's | P: C itself when no state commit follows it (as today), H when only state commits do, or a state commit in between when a later merge follows them |
| | otherwise: a state commit after a later merge | nothing; names the first later merge |

"P's state blob is H's" is compared by blob id (`git rev-parse P:tofu/terraform.tfstate`). That's the condition that
matters: a plan is right exactly when its state is `main`'s. It keeps today's behaviour for every run that wasn't
affected, including a merge followed by later merges that nothing has applied yet.

The middle sub-case is A, then an apply's state commit S, then a later merge B: A's run plans S, which is A's
declaration with the current state. So A is applied even if B's CI fails (side-agent review, 2026-10-26). Without
it, A would wait for B's run, which never comes if B's CI fails.

Only one case plans nothing: an apply has committed state *after* a later merge B. That apply planned `main`'s head
at its time, usually B or later, so it already applied A's declaration. The exception is an apply whose plan was made
before A merged and approved after B landed. Then A's changes wait for B's run, or, if B's CI fails, for the next
daily or manual run (Risks).

**Alternatives considered:**
- **Plan nothing when a state commit names C**, as #167's first route says. It handles #167, but not two merges in a
  row: the second merge's run finds a state commit naming the first, not itself, and would still plan with stale
  state. And it reads the commit message, a second record of what the state already shows. Planning H covers both,
  and in #167's case shows "No changes", which asks nothing.
- **Always check out C, then overlay H's state file.** If a scheduled run had applied a later merge, C's declaration
  with that state would plan to undo the later merge. Refused.
- **Always plan H in a `workflow_run`.** It could plan a later merge whose CI hasn't passed, or has failed, which is
  what `workflow_run` exists to prevent.

### D2. A state commit is identified one way

The script holds the state path and the App's bot address, and decides "is this a state commit" with one function,
used both for C and for each commit in C..H. The workflow passes `STATE_AUTHOR` from its `env`, so the address stays
written once. The inline skip step goes. `test_required_checks.py`'s check that the skip reads the path CI ignores
moves to the script's constant.

### D3. What the job does with the answer

- The job's first step checks out `main` with full history (`ref: main`, `fetch-depth: 0`), so H is `main` as it is
  now and C..H can be walked.
- The script prints `sha=`, `plan=true|false`, and writes a line to the step summary: which commit is planned and why,
  or why nothing is. It exits non-zero only for the refusal (C not on `main`) or an input it can't read: a malformed
  event name or commit is an error, never "plan nothing".
- Then `git checkout --detach "$sha"` when there's a plan. Every later step's `if` reads the script's `plan` output,
  where it read the skip's before. The guard wait, the plan's heading, the apply's checkout and `--planned` all use
  its `sha`.
- When the planned commit is H, a state commit, the state commit after the apply names H. It names what was applied,
  as the spec asks.

### D4. Tests

- `scripts/tests/test_plan_target.py` builds a real repository per case with the conftest's `git` helper: state
  commits made with the App's address and only the state file, merges made as the tester. One test per row of D1,
  plus a merge commit that changes the state file under someone else's name (break-glass) not counting as a state
  commit. Each test is named for the answer it checks.
- A workflow test parses `tofu.yml`: the plan job runs the script before the commit is checked out, every later step
  is gated on its `plan` output, and the `sha` output, the guard wait and the apply's checkout read the script's
  `sha`. Mutation cases break each link and expect a named problem, like `test_plan_display_workflow.py`.

## Risks / Trade-offs

- [A later merge's CI fails after an earlier merge's run planned nothing for it] → this needs the one case in D1 that
  plans nothing: an apply whose plan predates the earlier merge, approved after the later one landed. Neither merge is
  applied by a `workflow_run` then. The daily run, or one started by hand, plans `main`'s head, which includes the
  failed merge's declaration. That's already true today of any merge whose CI fails, and before this change the
  earlier run would have planned stale state, so nothing that worked stops working.
- [A merge lands between the script's decision and the plan] → the plan still reads current state: merges don't
  change state, and state commits can't land while this run holds the group.
- [The planned commit isn't the one the run's title names] → the summary names both (D3), and the apply's state
  commit names the one applied.
- [The scheduled run still applies a merge before its CI is green] → unchanged by this design. See Open Questions.

## Migration Plan

No state or `tofu/` change. The pull request's plan shows no changes. After the merge, its own `workflow_run` run is
the first to use the script: its summary should say it planned its own commit, as its state is current. Rollback is a
revert.

## Open Questions

- **Should a scheduled or manual run wait for CI on `main`'s head before it can apply?** ci-apply's design D1 says an
  apply follows green CI and guard, and a scheduled run waits only for the guard. This design makes a scheduled apply
  of a merge harmless, so it doesn't depend on the answer. It's for the owner to decide, as its own issue if wanted.
