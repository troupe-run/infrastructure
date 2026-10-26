# Plan each merge once, against main's current state

## Why

On 2026-10-26, PR #165's merge `d5ba974` was applied twice (#167). The daily run, started late, planned `main`'s head
before CI on the merge finished, and the owner approved it. Then CI finished, and the merge's own `workflow_run` run
checked out `d5ba974`. Its state file was the one from before the first apply, so it planned the same two updates
again, and the owner approved those too. The apply left empty commits in troupe and website, cancelled two legs of
troupe's `check`, and only then did `commit_state.py`'s 409 notice.

The cause is wider than the schedule. A run on `main` plans the commit it was started for, with that commit's
`tofu/terraform.tfstate`. When an apply has committed new state since, that file is stale. The same thing happens
without a schedule: two merges in a row, where the second's run waits behind the first's approval. The second run
then checks out its own commit, whose state is from before the first apply, and plans the first merge's changes
again. The spec's "Applies don't overlap" says it "plans against the state the first left". Today it doesn't.

## What Changes

- **A plan of `main` reads `main`'s current state.** Before it plans, the `plan (main)` job decides which commit to
  plan, from `main` as it is when the job starts, not when the run was triggered. A new script,
  `scripts/plan_target.py`, makes that decision in one place, and the job's later steps and the apply use the commit
  it names.
- **A scheduled or manual run** plans `main`'s head at the time the job starts. The commit it was triggered on may be
  older, if the run waited behind another.
- **A run after CI on a merge** (`workflow_run`), for commit C:
  - C is the App's state commit: plan nothing, as today (the inline check moves into the script).
  - C's state file is `main`'s current one: plan C, as today.
  - Only the App's state commits follow C on `main`: plan `main`'s head, which is C's declaration with the state those
    applies left. When one of them already applied C, as in #167, the plan shows no changes and asks for no approval.
  - State commits follow C, then a later merge, and no state commit after it: plan the last of those state commits.
    It is C's declaration with the current state, so C is applied even if the later merge's CI fails.
  - An apply has committed state after a later merge: plan nothing. That apply nearly always covered C already, and
    otherwise the later merge's own run plans C's changes with the current state. If that merge's CI fails, C waits
    for the next daily or manual run, which plans `main`'s head, failed merge included. That's what happens today to
    any merge whose CI fails (design, Risks).
  - C isn't on `main`'s history: fail, naming the commit. It is never planned on a guess.
- **The run's summary says which commit was planned and why**, or why nothing was.
- **The README's "Running a plan"** says which run applies a merge.
- **Tests:** `scripts/tests/test_plan_target.py` drives the script against real temporary repositories, one test per
  case above, and a workflow test pins that the plan and apply use the script's answer.

**A deviation from #167's first route, on purpose.** The issue asks that a run for an already-applied merge "plans
nothing". This change plans `main`'s head instead, which shows no changes and asks nothing. Telling "already applied"
apart would mean reading the state commit's message, a second record of the same fact. And the same rule is what
makes the two-merges case right, where planning nothing would leave the second merge unapplied.

**#167's second route isn't taken.** A scheduled or manual run still doesn't wait for CI on `main`'s head. With the
change above, a scheduled run that applies a merge first is harmless: the merge's own run then plans the state it
left. Whether a scheduled apply should also wait for green CI (design D1 of ci-apply says an apply follows green CI
and guard) is a separate question. It's raised in the design as an open question, not decided here.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: an ADDED requirement that every plan of `main` reads `main`'s current state, with scenarios for a merge
  already applied by another run, two merges in a row, a later merge, and a scheduled run that waited. No existing
  requirement's text changes; "Applies don't overlap" becomes true as written.

## Impact

- `.github/workflows/tofu.yml`: the `plan (main)` job fetches `main`, runs `scripts/plan_target.py` first, and checks
  out, waits for the guard on, plans and hands the apply the commit it names. The inline "Skip the App's own state
  commit" step goes.
- `scripts/plan_target.py`: new. Standard library and `git` only.
- `scripts/tests/test_plan_target.py`: new. A workflow test for the job's wiring.
- `README.md`: "Running a plan".
- No change to `tofu/`, so the plan of this change's pull request shows no changes. Nothing is delivered to troupe or
  website: `tofu.yml` isn't a guard file.
- Closes #167.
