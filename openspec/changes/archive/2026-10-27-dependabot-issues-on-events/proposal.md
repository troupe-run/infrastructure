# Proposal

## Why

`dependabot-issues` (#172) runs on a `*/10` schedule that has never fired (#195). Every schedule in this org runs
hours late, and this one runs not at all. So a new Dependabot pull request gets no issue, and a rebased one stays red
on `pr-closes-issue` until someone starts the workflow by hand. The work comes in bursts, just after Dependabot acts,
so the run should start then too, and a run that never comes should be reported, not go unnoticed.

## What Changes

- **Dependabot's own runs start the workflow.** Every completed "Dependabot Updates" run starts `dependabot-issues`,
  within an hour. These are the runs that open, rebase and supersede pull requests.
  - In infrastructure, `dependabot-issues.yml` runs on `workflow_run` of "Dependabot Updates".
  - In troupe and website, a new delivered workflow, `.github/workflows/dependabot-dispatch.yml`, runs on the same
    event and dispatches infrastructure's `dependabot-issues` with a token. It checks out nothing and reads nothing
    from the event.
- **A new App, `troupe-run-dispatch`**, created by the owner, has Actions write and nothing else, and is installed on
  infrastructure only. Its key is a secret in a main-only `dependabot-dispatch` environment in troupe and in website.
  Its client ID is a repository variable in both. This follows the docs App's pattern.
- **The `*/10` schedule goes. A daily backstop replaces it.** The backstop does the same work. When it finds an open
  Dependabot pull request that has been missing its issue or closing line for over an hour, an event was missed. It
  fixes the pull request, reports it in one tracking issue in infrastructure, and the run fails. A clean backstop
  closes the tracking issue.
- **The schedule watch watches the backstop**, with a 2-day limit, so a schedule that never fires is reported too.
- The dispatcher is one of the guard's delivered files. It's protected by the delivered-file rule there, and
  Dependabot leaves it out like the other delivered workflows.
- The docs and the runbook drop the step of running the workflow by hand after Dependabot acts.

## Capabilities

### New Capabilities
- `dependabot-dispatch-credentials`: the `troupe-run-dispatch` App, its installation on infrastructure only, the
  main-only `dependabot-dispatch` environments in troupe and website that hold its key, and the variable that names
  it.

### Modified Capabilities
- `dependency-updates`: what starts `dependabot-issues` changes, from a 10-minute schedule to Dependabot's runs, a
  dispatch from troupe and website, a daily backstop, and by hand. The bound is one hour. A missed event is reported
  in a tracking issue. troupe's delivered workflows left out of Dependabot now include the dispatcher.
- `schedule-watch`: the declaration also lists infrastructure's `dependabot-issues.yml`, with a 2-day limit.

## Impact

- `.github/workflows/dependabot-issues.yml`: triggers, the backstop flag, and a handover of the tracking issue to
  the board job.
- New `.github/workflows/dependabot-dispatch.yml`, added to `guard_files` in `tofu/guard_delivery.tf`, and delivered to
  troupe and website.
- `scripts/dependabot_issues.py`: reports misses and keeps the tracking issue on a backstop run. Tests to go with it.
- `tofu/`: new `dependabot_dispatch.tf` (environments, deployment policies, variables). Regenerated
  `tofu/dependabot/*.yml` (the new exclusion). `oob/app-installations.json` gets the new App.
- `scripts/watched-schedules.json`, `scripts/tests/test_main_only_environments.py`, and new workflow tests.
- `docs/development-workflow.md`, `oob/README.md` (setting the new key) and the memory's by-hand step.
- Owner actions: create the App, set its key in two environments, and approve the plan and its delivery.
- Out of scope: watching `tofu`'s daily plan (named in #195, but a separate change), and a person closing a
  Dependabot pull request, which is still handled by the backstop.
