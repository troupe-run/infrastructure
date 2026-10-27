# Design

## Context

See proposal.md for why. What this builds on:

- **`dependabot-issues`** (archived change `2026-10-27-dependabot-issues`, design D1 to D8). One workflow in
  infrastructure covers troupe, website and infrastructure. `scripts/dependabot_issues.py` works out everything from
  GitHub on each run, so any run finishes what an earlier one didn't. Its `issues` job mints the
  `troupe-run-dependabot` App's token in the main-only `dependabot-issues` environment. Its `board` job adds the
  issues to the board with the board App. It holds `concurrency: dependabot-issues`, `cancel-in-progress: false`.
- **Dependabot's activity is visible as a workflow.** Each repository has the dynamic workflow "Dependabot Updates"
  (`dynamic/dependabot/dependabot-updates`, state `active` in infrastructure). Its runs are the ones that open,
  rebase, supersede and close Dependabot's pull requests.
- **GitHub's restrictions on Dependabot's events.** GitHub's troubleshooting page names `push`, `pull_request`,
  `pull_request_review` and `pull_request_review_comment` as the events whose Dependabot-triggered runs get a read-only
  token and only Dependabot secrets. `workflow_run` isn't named. Whether it's restricted isn't documented either way,
  which is the gap D1 of `dependabot-issues` left open. Task 1 probes it.
- **The docs App is the pattern for a cross-repository dispatch** (spec docs-build-credentials): `troupe-run-docs` has
  Actions write on website only, and its key is in main-only `docs` environments in troupe and infrastructure.
- **The guard's delivered files** (`guard_files` in `tofu/guard_delivery.tf`) go to troupe and website, are listed in
  each `.github/guard-delivery.json`, and are protected there by the delivered-file rule. `scripts/dependabot_config.py`
  leaves the delivered workflows out of Dependabot's `github-actions` entries there. `claude-review.yml` joined the
  list this way, and runs in infrastructure as well.
- **The schedule watch** (`scripts/watched-schedules.json`, `watch_schedules.py`) reports a declared workflow whose
  latest scheduled run is older than its limit, or never happened, in one tracking issue. It's also the pattern for a
  tracking issue that opens, comments only on change, and closes clean.

## Goals / Non-Goals

**Goals:**
- Starting the run needs nothing from a pull request: the trigger runs from `main`, reads nothing from its event, and
  checks out nothing in troupe or website.
- Every way the event path can fail ends in the same place, the backstop's tracking issue. That covers no event, a
  dispatch that fails, or a key that's missing. The schedule watch covers the backstop itself.

**Non-Goals:**
- **Starting a run when a person closes or merges a Dependabot pull request.** A merge closes the issue through its
  `Closes` line. A person's close waits for the backstop, which the spec allows.
- **Watching `tofu`'s daily plan.** #195 notes it's unwatched. It's a separate change.
- **Passing which pull request changed.** Each run reads everything, so the dispatch carries no inputs.

## Decisions

### D1. The trigger is `workflow_run` of "Dependabot Updates"

infrastructure's `dependabot-issues.yml` gains:

```yaml
on:
  workflow_run:
    workflows: ["Dependabot Updates"]
    types: [completed]
  schedule:
    - cron: "37 4 * * *"
  workflow_dispatch:
```

- **Why `workflow_run`:** it runs the workflow file on the default branch, in the base repository's context, so the
  `main`-only environment admits it. It's started by the run that changed the pull requests, not by the pull request.
  Every kind of Dependabot activity that drops a closing line or needs an issue happens in such a run.
- **`completed`, any conclusion.** A failed Dependabot run may still have opened or rebased a pull request.
- **Nothing from the event is read** (spec). The only `github.event_name` use is choosing the backstop mode (D4). A
  test pins that no expression reads `github.event.`.
- *Rejected: `pull_request` / `pull_request_target` from Dependabot.* Only Dependabot secrets or none, the pull
  request's context in a writing job, and in troupe and website the key would have to be a Dependabot secret that any
  Dependabot pull request's workflows can read.
- **If the probe shows `workflow_run` from Dependabot Updates doesn't fire, or gets no environment secrets**, the
  approach changes, so apply stops and asks the owner with the findings. It doesn't fall back to a Dependabot secret.

### D2. troupe and website dispatch with a dispatch-only App

`.github/workflows/dependabot-dispatch.yml`, delivered to troupe and website as one of the guard's files:

- On `workflow_run` of "Dependabot Updates", `completed`. `permissions: {}`. One job, `if: github.repository !=
  'troupe-run/infrastructure'`, because infrastructure holds the file as its source and is started directly (D1).
- The job uses the `dependabot-dispatch` environment (main only), mints `troupe-run-dispatch`'s token with
  `owner: troupe-run`, `repositories: infrastructure`, `permission-actions: write`, and runs
  `gh workflow run dependabot-issues.yml -R troupe-run/infrastructure --ref main`. No checkout, no inputs.
- **Why a new App** (the owner's choice, 2026-10-27): Actions write on infrastructure only. A leaked key can start,
  cancel or disable workflows in infrastructure, but it can't write issues, pull requests or code. A `tofu` apply
  still needs the owner's approval of its environment. *Alternatives the owner declined:* widening
  `troupe-run-dependabot` with Actions write and copying its key into three repositories, or running the script in
  each repository with that key.
- **Why delivered with the guard:** the delivered-file rule then protects it in troupe and website. Dependabot leaves
  it out (spec: delivered workflows), and delivery needs nothing new. The targets match: the guard goes to exactly the
  repositories other than infrastructure that have Dependabot.
- **`DISPATCH_APP_CLIENT_ID`** is a repository variable in troupe and website. `DISPATCH_APP_PRIVATE_KEY` is each
  `dependabot-dispatch` environment's secret, set by the owner (`oob/README.md`), as with the docs key.
- New `tofu/dependabot_dispatch.tf` declares the two environments, their main-only policies and the two variables, with
  `prevent_destroy` like the other credential environments. `test_main_only_environments.py` gains both.

### D3. Concurrency already coalesces a burst

Dependabot's weekly run is many "Dependabot Updates" runs, each starting `dependabot-issues`. The existing
`concurrency: dependabot-issues` with `cancel-in-progress: false` keeps one run in progress and one pending, and a newer
pending run replaces the older one. So a burst ends with a run that starts after the last trigger, which is all a run
needs, since each run reads everything. The replaced runs show as cancelled, which is expected. It stays unchanged,
and the design comment in the workflow says why.

### D4. The daily backstop counts misses, and only misses

A run started by `schedule` passes `--backstop` to the script, and so does one started by hand with the boolean
input `backstop` set, so the path can be proved without waiting for the schedule. Without it, the script behaves
exactly as now.

- **A miss** is an open Dependabot pull request that, when the run reads it, needs a new issue or relink (D2 step 1 of
  `dependabot-issues`), or its closing line (step 3), and whose `updated_at` is over an hour old (spec). A pull request
  updated within the hour may have an event run on its way, so it's fixed but not counted.
- **Not a miss:** closing an issue for a merged pull request, closing as not planned after the hour, or reopening an
  issue. Only time or a person's action makes that work due, so no event could have done it. That's the side agent's
  point (2026-10-27), and the spec's "Work only the backstop can do".
- **`updated_at`** moves on any activity, such as a comment. A person's comment can only delay a miss by a day. It can't
  invent one, so the error is toward silence for one day, never a false alarm.
- **The hour** is the spec's bound, kept as one constant in the script.
- **Every write happens first.** The misses are then reported and the run exits 1. A run that also failed a repository
  still exits 1, and its message names both.

### D5. Misses go to one tracking issue, opened by the Dependabot issues App

- In infrastructure, titled "Dependabot events missed", opened, commented on and closed with the
  `troupe-run-dependabot` token the `issues` job already has. It has Issues write on infrastructure.
- It follows the schedule watch's rules (spec): open when misses and none open; comment only when the set of missed
  pull requests differs from the last report, read from a marker in the latest App comment or the body; close clean
  with a comment linking the run; ignore issues with that title by anyone else; when two are open, update the oldest.
  The script reuses the watch's approach but keeps its own code: `watch_schedules.py` writes with `GITHUB_TOKEN`
  and its decision function is shaped around its own problems. A shared module is a refactor this change doesn't need.
- **It carries no `dependencies` label and no `dependabot-issue` marker**, so the script's own issue listing never
  treats it as an update's issue.
- **Its URL joins `issue-urls`**, so the existing board job puts it on the board, already restricted to issue URLs in
  the three repositories.
- *Rejected: only failing the run.* GitHub emails a scheduled run's failure to whoever last changed the cron, which
  isn't a dependable reader. *Rejected: reporting through the schedule watch.* It reports schedules that stop, not
  runs that fail, and `links-weekly` failing isn't a stopped schedule.

### D6. The watch watches the backstop

`scripts/watched-schedules.json` gains `{"repository": "infrastructure", "workflow": "dependabot-issues.yml",
"max_age_days": 2}`. Schedules here run 3 to 6 hours late, so 2 days allows one missed day without a false report.
Only scheduled runs count (spec schedule-watch), so the event runs don't hide a dead schedule.

### D7. The cron

`37 4 * * *`. Off the hour, since GitHub's load peaks on the hour, and before the 06:00 plan. The time doesn't matter
otherwise: it runs late either way.

## Risks / Trade-offs

- **[Risk] `workflow_run` from Dependabot Updates gets no secrets, or doesn't fire.** → Task 1 probes it on a throwaway
  repository before anything else is built. If it fails, apply stops and asks the owner (D1).
- **[Risk] `workflow_run` doesn't fire in a repository where the workflow file isn't on the default branch yet.**
  After the delivery it is on `main`. → The migration starts a Dependabot run by hand and checks the chain end to end.
- **[Risk] A dispatch-only token can disable infrastructure's workflows, guard included.** → The key is readable only
  by a `main` run in troupe or website, which only the owner's approved changes reach. The same exposure exists for
  `troupe-run-docs` on website. A disabled workflow shows on the next pull request, whose required check never
  reports.
- **[Risk] A person's close of a Dependabot pull request leaves its issue open for up to a day.** → Accepted (spec).
  It isn't reported as a miss.
- **[Trade-off] Up to two `dependabot-issues` runs per Dependabot run** (dispatch plus concurrency). Each one with
  nothing to do makes only reads. Actions minutes are free on public repositories.
- **[Risk] The board App's add retries.** Unchanged from `dependabot-issues` D7: the board job re-checks every run.

## Migration Plan

1. **The owner creates `troupe-run-dispatch`** (Actions write, Metadata read, no organisation permission, installed on
   infrastructure and a throwaway `troupe-run/infra-probe-dependabot-dispatch`), and records its client ID on #195.
2. **Probe** on throwaway repositories (public, named `infra-probe-*`): one with Dependabot and a `workflow_run` of
   "Dependabot Updates" workflow using a main-only environment secret, checking that it fires and reads the secret.
   Then the dispatch: a token minted for the App starts `workflow_dispatch` in the target, and is refused 403 on a
   contents write, an issue, and another repository. Record the results in tasks.md. Delete the repositories and
   remove them from the App afterwards.
3. Build and test. Open the pull request. Its plan shows the two environments, policies and variables, and the
   delivered `dependabot-dispatch.yml` and new `guard-delivery.json` to troupe and website, plus regenerated
   `dependabot.yml`s.
4. After the merge and the apply, the owner sets `DISPATCH_APP_PRIVATE_KEY` in troupe's and website's
   `dependabot-dispatch` environments (oob/README.md).
5. Check end to end. Comment `@dependabot rebase` on a Dependabot pull request that's behind `main` in each of troupe,
   website and infrastructure. Check a `dependabot-issues` run starts after each Dependabot run, and the closing line
   is back within the hour. Start the workflow by hand with `backstop` set while nothing is missed, and check that it
   succeeds and opens no tracking issue. Then check the first scheduled run happens, and the watch's next run finds no
   problem for `dependabot-issues.yml`.

Rollback: revert the workflow's triggers to `workflow_dispatch` only and run it by hand as now. Removing the
dispatcher from `guard_files` deletes it from troupe and website on the next apply.
