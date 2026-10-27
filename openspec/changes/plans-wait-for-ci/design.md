# Design

## Context

See proposal.md for why. The current state this design works from:

- `tofu.yml`'s `plan (main)` job runs on `workflow_run` (CI completed with success on `main`), `schedule` and
  `workflow_dispatch`. It checks out `main` with full history, then `scripts/plan_target.py` names the commit to plan:
  `main`'s head for a scheduled or manual run (plan-each-merge-once D1-D3). It then waits for the guard check on that
  commit with an inline `gh run list` loop (60 polls of 10 s), and plans. The job's timeout is 30 minutes.
- `ci.yml` runs on `push` to `main` with `paths-ignore: [tofu/terraform.tfstate]`, so it doesn't run for a push that
  changes only the state: the App's state commits, and a break-glass state commit merged by pull request (README,
  "Break-glass"). GitHub applies `paths-ignore` to the whole push, so a rebase merge whose last commit changes only
  the state still gets a CI run, on that last commit. Its concurrency group cancels an older `main` run when a newer
  push lands. Its longest job timeout is 20 minutes (`guard tests` legs, on three OSes).
- The workflow token has only `contents: read`. The guard wait already reads workflow runs with it: this repository is
  public, so reading its runs needs no `actions` permission.
- The `drift (out of band)` job runs on the same events as the plan, and depends on nothing.
- A re-run of a failed CI run on `main` ends in a new `completed` event, so a passing re-run starts the merge's own
  `workflow_run` plan.

## Goals / Non-Goals

**Goals:**
- A scheduled or manual plan of `main` never plans a commit whose CI hasn't passed.
- A red `main` shows up as a failed run that says what to do, every day until it's green.

**Non-Goals:**
- Changing the run after CI on a merge. It follows CI's success already.
- Gating the guard check differently. Its wait stays as it is.
- Gating the drift job (D5).
- Re-checking CI between the plan and the apply. The apply applies the saved plan of the commit that was checked; a
  newer merge gets its own run.

## Decisions

### D1. A script, `scripts/main_ci.py`, run as one step of the plan job

The gate is a Python script, standard library plus `gh`, run with the runner's `python3` like `plan_target.py`. It
takes `--main origin/main`, `--summary "$GITHUB_STEP_SUMMARY"` and the repository, and exits 0 only when CI passed.
`gh` and the clock are passed in, so the tests drive every outcome without GitHub or real waiting.

The step runs right after `The commit to plan`, gated on
`github.event_name != 'workflow_run' && steps.target.outputs.plan == 'true'`, and before the guard wait. Every later
step already depends on the job not having failed, so a failed gate stops the plan.

*Alternatives:* an inline bash loop like the guard wait. Rejected: the commit walk (D2) and the outcomes (D3) need
tests, and the guard wait has none. Folding it into `plan_target.py`: rejected, since that script answers which commit
has `main`'s current state, using only git; this one answers whether CI passed, using GitHub. Keeping them apart keeps
each decision in one place.

### D2. Which commit's CI: the one CI runs on for `main`'s head

The issue says "the newest commit on `main` that isn't the App's state commit". That misses two cases CI's
`paths-ignore` creates: a break-glass state commit merged by pull request (by a person, changing only the state, so CI
never runs and the gate would wait until its limit), and a rebase merge whose last commit changes only the state (CI
runs on that last commit, not the one before it). So the rule follows CI's trigger, not the commit's author.

Walking `main`'s first-parent history from its head:

1. A commit with a CI `push` run (`gh run list --workflow ci.yml --commit <sha> --event push --branch main`) is the
   one. Its newest run decides (D3).
2. Otherwise a commit that changes only `tofu/terraform.tfstate` is one CI skips: look at its parent.
3. Otherwise this commit is the one, and CI hasn't started on it yet: wait (D3).

The walk runs again at every poll, so a run that appears on a later commit of the same push (case 1 above, after a
step 2 skip) is found. It stops at the first commit that changes more than the state, so it reads at most that commit
and the state commits after it. The state file's path is `plan_target.STATE_PATH`, imported, not repeated, and a test
pins that `ci.yml`'s `paths-ignore` is exactly that path, so the two can't drift apart.

### D3. Outcomes, and a time limit

The newest CI run for the commit decides:

| CI run | The gate |
|---|---|
| none yet, or `queued`, `in_progress`, `waiting`, `requested`, `pending` | waits, polling every 15 s |
| `completed` with `success` | passes: says so in the summary, and the plan runs |
| `completed` with anything else (`failure`, `cancelled`, `timed_out`, `startup_failure`, ...) | fails (D4) |
| a status it doesn't know | fails, naming the status: an unknown value is an error, not "still running" |
| a `gh` read that fails | fails, with `gh`'s error |

The limit is 25 minutes, a constant in the script: CI's longest job may take 20, and macOS and Windows runners can
queue. The plan job's timeout rises from 30 to 45 minutes, so the gate always reports its own reason before GitHub
cancels the job. A test pins that the job's timeout is above the limit plus the guard wait's 10 minutes.

*Alternatives:* retrying a failed `gh` read. Rejected for now: the failed run reaches the owner, and a re-run of the
`tofu` run is the retry. Treating a cancelled CI run as "not decided yet": rejected, since a newer push is what
cancels a `main` run, and the walk would have found that newer commit first; a cancel on the newest is by hand, and
only a re-run makes it green.

### D4. What a red `main` says

The job fails with an `::error::` annotation and a summary section that names the commit (short sha and subject),
links the CI run, and lists the ways out:

- **Broken code:** merge a fix pull request. Its own run plans and applies once CI passes.
- **A flaky failure:** re-run the failed jobs (`gh run rerun <id> --failed`). When they pass, the merge's own run
  starts.
- **Something urgent:** a break-glass apply from the owner's machine (README, "Break-glass").

A timeout says CI didn't finish in 25 minutes, names the commit and links the run if there is one.

### D5. The drift job still runs whatever CI's result

It only reads, with a read-only token, so a red `main` can't make it change anything. Out-of-band drift should still reach
the owner while `main` is red, and the plan job's failure already reports the red `main`. So the drift job is left as
it is, and the spec gains a scenario that says so.

*Alternative:* gate it too. Rejected: it would hide out-of-band drift for as long as `main` stays red, for no safety
gained, since it writes nothing.

### D6. No way to skip the gate

`workflow_dispatch` keeps no inputs. A test pins that it has none, so a "skip CI" input can't be added without the
test changing in the same pull request.

## Risks / Trade-offs

- [A scheduled run waits behind CI for up to 25 minutes, holding the `tofu-main` concurrency group] → A merge's own
  run queues behind it, as it already queues behind an apply awaiting approval. Once CI passes, both plan; the second
  plans the state the first left (plan-each-merge-once).
- [A transient GitHub API error fails the daily run] → The failure names `gh`'s error; a re-run fixes it. If it shows
  often, retries can be added in the script without changing the spec.
- [`paths-ignore` in `ci.yml` changes later] → The test pinning it against `STATE_PATH` fails in the same pull
  request.
- [Rebasing this change carries a stale step condition] → The workflow test pins the gate step's `if:` and position
  (memory: rebase carries stale step conditions).

## Migration Plan

Merge as usual. The first scheduled run after the merge uses the gate. Rolling back is reverting the pull request. No
OpenTofu resources change.
