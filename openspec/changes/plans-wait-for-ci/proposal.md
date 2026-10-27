# Proposal

## Why

ci-apply's design D1 says an apply follows green CI and guard. A run after CI on a merge (`workflow_run`) does, but a
scheduled or manual run of `tofu.yml` waits only for the guard check. It can plan, and after approval apply, a commit
whose CI hasn't finished or has failed. On 2026-10-26 the daily run applied `d5ba974` while its CI was still running
(#167). PR #176 made that harmless for the merge's own run, but the gate is still missing (#178).

The owner, 2026-10-26: a red `main` holds scheduled runs until the build is green, and manual runs too. None of the
ways out of a red `main` needs a manual run, and a "skip CI" input would be a second way past the same gate.

## What Changes

- **A scheduled or manual run checks CI on `main` before it plans.** It finds the commit CI ran on, or will run on,
  for `main`'s head: the newest commit on `main`'s first-parent history that isn't a commit CI skips (one that changes
  only `tofu/terraform.tfstate`, which is what CI's `paths-ignore` leaves out: the App's state commits, and a
  break-glass state commit merged by pull request).
  - **CI passed:** the run plans as it does today.
  - **CI is still running, or hasn't started yet:** the run waits, up to a time limit, then plans or fails as below.
  - **CI concluded anything but success** (failure, cancelled, timed out, and so on): the run fails before planning.
    Its summary names the commit, links the CI run, and lists the three ways to recover: a fix pull request, a re-run
    of the failed CI job, or a break-glass apply from the owner's machine. The failed run is how a red `main` reaches
    the owner, so the daily drift check never stops quietly.
  - **CI didn't finish within the limit:** the run fails, saying so.
- **No way to skip the gate.** `workflow_dispatch` gets no input for it.
- **A run after CI on a merge is unchanged.** It already follows CI's success on that merge.
- **The `drift (out of band)` job still runs whatever CI's result.** It only reads, and drift outside OpenTofu should
  still reach the owner while `main` is red (design D5).
- **The gate is a script, `scripts/main_ci.py`,** standard library plus `gh`, with tests in `scripts/tests/` named for
  what they check, and a workflow test pinning where `tofu.yml` runs it.
- **The README's "Running a plan" section** says a red `main` holds scheduled and manual plans, and how to recover.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: a new requirement that a scheduled or manual plan of `main` waits for green CI on `main` and fails,
  saying how to recover, when CI failed (added). "What OpenTofu can't manage is checked whenever main is planned"
  gains a scenario: the drift job runs whatever CI's result (modified).

## Impact

- `.github/workflows/tofu.yml` (`plan` job: a new step before the guard wait, and a longer job timeout).
- `scripts/main_ci.py` (new), `scripts/tests/test_main_ci.py` and `scripts/tests/test_main_ci_workflow.py` (new).
- `README.md` ("Running a plan").
- No OpenTofu resource changes, so the plan of this change's pull request shows none.
- Not a guard file, so nothing is delivered to troupe or website.
- A scheduled run that starts while CI on `main` is running now takes up to the time limit longer.
