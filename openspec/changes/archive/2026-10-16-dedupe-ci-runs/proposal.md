# Proposal: CI tests a pull request once, and main after each merge

## Why

`.github/workflows/ci.yml` runs on `pull_request` and on `push` to every branch, so on a branch with an open pull
request every CI job runs twice. On #64 that was 31 check runs where about half would do: `check` and all eleven
`guard tests` legs ran twice, and the Windows and macOS legs take 2 to 3 minutes each (#66). Nothing reaches `main`
without a pull request, so a branch's `push` run tests what its `pull_request` run already tests (the branch merged
onto `main`), only less usefully (the branch's head on its own).

`main` runs the full matrix twice for each merge, too. After the merged commit's run, `tofu.yml` plans and applies,
and then the App commits the new state to `main`. That commit changes only `tofu/terraform.tfstate`, and it starts
CI's twelve jobs again (for example run 38898852538, on `5bcba8e`). Nothing reads the state file in those tests, and
the plan that follows the run skips the App's state commit anyway. Each of the last five merges did this.

## What Changes

- `ci.yml`'s `push` trigger narrows from `branches: ["**"]` to `branches: [main]`. A pull request is tested by its
  `pull_request` run alone. `main` is still tested after every merge, and `tofu.yml`'s plan of `main` still follows
  that run (`workflow_run` on `CI`, branch `main`).
- `ci.yml`'s `push` trigger ignores a push that changes only `tofu/terraform.tfstate`, so the App's state commit
  doesn't run CI again. `guard` still runs on it, and the daily plan still plans it.
- The comment at the top of `ci.yml` says when it runs and why.
- Tests pin `ci.yml`'s triggers, as `guard.yml`'s already are in `scripts/tests/test_required_checks.py`, and tie
  them to what `tofu.yml` follows.

Out of scope:

- **`guard.yml` keeps running on every push and every pull request.** The `development-workflow` spec ("The rules are
  re-checked on GitHub") requires the rules to be re-applied "for every push to any branch and for every pull
  request", so a branch pushed with no pull request is still checked. The file is also delivered to troupe and the
  website. It's one job of about 10 seconds. The issue left it to the owner, who decided on 2026-10-16 to leave it
  as it is.
- `main`'s run on the merged commit stays, with all twelve jobs. `main` doesn't require a branch to be up to date
  before merging (`strict_required_status_checks_policy = false`, so the App's state commits don't hold up every pull
  request), so the merged tree can be one no pull request run tested. A delivery is planned only after CI is green
  on all three OSes for the commit being delivered.
- troupe's `ci.yml`. It already runs `push` on `main` only (`pull_request` plus `push: branches: [main]`, checked on
  troupe's `main` on 2026-10-16), so troupe needs no issue. troupe has no state commit.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: a new requirement, "CI tests each pull request once, and main after every push". No spec says yet when
  `ci.yml` runs, though "Main is applied only after the owner approves its plan" depends on CI running on every push
  to `main`.

`rulesets` needs no change. The required checks are the jobs a pull request reports, and those don't change.

## Impact

- `.github/workflows/ci.yml`: the trigger, and its comment. OpenTofu doesn't read the file, but
  `scripts/plan_needed.py` counts any path it doesn't list as read, so the pull request is planned once the owner
  approves that run. The plan should show no changes.
- `scripts/tests/test_required_checks.py`: two more tests.
- A branch pushed without a pull request no longer gets CI until a pull request is opened. `guard` still checks it,
  and every commit on it has passed `scripts/check.py` locally (development-workflow, "Checks pass before a
  commit").
- Each pull request update runs twelve fewer check runs. #64's head commit reported 31: `check` and the eleven
  `guard tests` legs twice each (24), `guard (workflow rules)` twice, and `DCO` and four `tofu` jobs once. It would
  report 19.
- Each merge that is applied runs CI on `main` once instead of twice: twelve fewer jobs.
