# Design

## Context

- **The check today** (`scripts/guard.py`, `delivered_changes_by_others`). `guard.py ci` passes a commit that changes
  a delivered file when `git log --format=%ae` equals `DELIVERY_AUTHOR_EMAIL`, the App's bot. That is the commit's
  self-declared author.
- **The check judges itself.** `.github/workflows/guard.yml` checks out the pushed commit and runs
  `scripts/guard.py` from it. Both are delivered files. A push that forges the author can also change the guard, and
  the `guard` check then runs the changed copy. So hardening the author check (for example, verifying GitHub's
  signature on the commit) would not close the gap on its own. The enforcement has to be outside the pushed tree.
- **The delivered paths** are declared once, in `tofu/guard_delivery.tf`: `local.guard_files` plus
  `local.guard_list_path`, merged into `local.guard_contents`. Only `troupe` receives them (`local.guard_targets`).
- **The rulesets today** (`tofu/modules/repository/main.tf`) all target `branch`: `protect main` on `troupe`,
  `infrastructure` and `website`, and `app only` on `.github`. The App (`local.infrastructure_app_id`) bypasses with
  `always` on `troupe`, `infrastructure` and `.github`.
- **What GitHub says about push rulesets.** A push ruleset can "prevent commits that include changes in specified
  file paths from being pushed", and covers the repository's whole fork network. GitHub's docs and changelogs
  (push rules GA, 2024-09-10; path exceptions, 2026-08-25) describe push rulesets for **private and internal**
  repositories, on Team and Enterprise. Branch rulesets are on Free for public repositories. `troupe` is public, on
  Free. Nothing found says outright that a public repository is refused, which is why the issue asks for a probe.
- **The provider** is `integrations/github` 6.13.0. `github_repository_ruleset` documents `target = "push"` and a
  `file_path_restriction { restricted_file_paths }` rule. This is to be confirmed against the provider's schema
  (task 1.1).

## Goals / Non-Goals

**Goals:**
- A change to a delivered file in a governed repository is refused by GitHub, whoever the commit claims as its
  author, on any branch and through any route (git push, web editor, contents API).
- The App's deliveries still land, and nothing else in `troupe` is refused by the new rule.
- The restricted paths can't drift from the delivered files.
- If GitHub can't refuse the change on a public repository, a forged edit shows in a plan within a day (D5).
- Every GitHub behaviour this relies on is shown on a throwaway repository first.

**Non-Goals:**
- Changing `scripts/guard.py`. Its author check stays as it is.
- Restricting delivered files in `infrastructure`, which is their source.
- Making the `guard` check run a copy of itself that the push can't change (Risks; a follow-up issue, D5).

## Decisions

### D1. Probe before anything live

On `troupe-run/infra-probe-<yyyymmdd>` (public, with a README, added to the App's installation by the owner), driven
by `tofu/probe` with a new `probe_delivered_paths` variable passed to the module:

1. **Create the ruleset.** Apply it through the probe. If GitHub refuses to create a push ruleset on a public
   repository, record the response; that answers the question, and the probe skips to step 6.
2. **The App delivers.** With `probe_delivery = true` and `probe_delivery_bypass = true`, the App's delivery of the
   guard's files to `main` is accepted. Steps 3 and 4 are done with the owner's credentials, which is the strongest
   non-App identity, since an org owner has no bypass here.
3. **A forged push is refused.** Commit a change to `scripts/guard.py` with
   `--author "troupe-run-infrastructure[bot] <340938853+troupe-run-infrastructure[bot]@users.noreply.github.com>"`,
   push it to a new branch, then try it straight to `main`. Both are refused, naming the ruleset.
4. **Other routes are refused, and nothing else is.**
   - An edit to `.github/guard-delivery.json` through `gh api -X PUT repos/troupe-run/<probe>/contents/...` is
     refused.
   - A new branch pushed from `main`, whose history already holds the App's deliveries, is accepted.
   - A branch whose commits change only `README.md` is accepted.
5. **A list change follows.** Removing a path from `probe_delivered_paths` and re-applying lets a push to that path
   through.
6. **Clean up.** Record the findings under D1 and in the adopt-org findings memory, delete the repository, and
   remove the probe's local state and `terraform.tfvars`.

The probe uses the owner's `gh` login only against `troupe-run/infra-probe-*`, which the guard exempts. Pushing a
forged author there is a test of GitHub, not a workaround of the guard.

### D2. One push ruleset per governed repository, over the delivered paths

The module gains `delivered_paths` (a list of strings, default `[]`). When it isn't empty, the module adds a ruleset
named `delivered files`:
- `target = "push"`, with no `conditions` block, since a push ruleset covers every ref;
- one rule, `file_path_restriction`, with `restricted_file_paths = var.delivered_paths`;
- one bypass actor: the App in `app_bypass_id`, `Integration`, `always`. A precondition refuses `delivered_paths`
  without `app_bypass_id`, since nothing could then deliver (as `app only` does).

`troupe`'s module gets `delivered_paths = local.guard_delivered_paths`. That local is defined in
`tofu/guard_delivery.tf` as `sort(keys(local.guard_contents))`, the same set the delivery resource iterates, so
the two can't disagree.

Exact paths, not globs. The delivered set is short and closed, and a glob like `.githooks/*` would also restrict a
file troupe adds there itself.

*Alternatives:*
- **A rule in `protect main`:** not possible. A file path restriction is a push rule, and `protect main` is a branch
  ruleset.
- **An org-level ruleset over every governed repository:** org rulesets need Team. It would also move the
  per-repository list away from the delivery that defines it.
- **Covering `main` only:** a push ruleset can't be scoped to a branch, and it shouldn't be. A delivered file
  changed on a branch is already wrong, and refusing the push is the earliest point to say so.

### D3. No bypass but the App's, the owner included

The owner changes a delivered file at its source, here. An owner bypass would let an agent holding the owner's
credentials do exactly what the rule forbids. That mirrors `protect main`'s refusal of direct pushes by the owner.
The break-glass is editing or disabling the ruleset on GitHub, which the next plan shows and an apply restores
(rulesets spec, "The owner can't be locked out"). This takes the side that can't lock the owner out: the owner keeps
org administration, so the ruleset itself is always editable.

### D4. The guard's author check stays, recast

No change to `scripts/guard.py`. Its hook refusals and its CI check catch an honest mistake before the push, with the
guard's usual message and fix. The guard-delivery spec now says GitHub enforces the rule and the guard's checks are
there to catch mistakes early (spec delta). `docs/development-workflow.md` says the same. Its Known gaps entry is
replaced by what's left: the owner's break-glass, which shows as drift.

### D5. If the probe says no: a plan of `main` every day

Decided by the owner on 2026-10-13, so apply carries on after the probe on either path. This is the issue's
approach 2. A forged edit isn't refused, but it shows in a plan within a day of landing, and the apply the owner
approves restores the file.

- **The trigger.** `tofu.yml` gains `schedule: - cron: "0 6 * * *"` (06:00 UTC, 16:00 or 17:00 in Melbourne). A
  scheduled run is on the default branch, so it reaches the `plan-main` environment like a merge's run does.
- **The `plan (main)` job runs for it.** Its `if` accepts `github.event_name == 'schedule'` alongside
  `workflow_dispatch`. The commit planned is `github.sha`, which is `main`'s head.
- **No skip on the state commit.** "Skip the App's own state commit" exists so the App's commit after an apply
  doesn't plan again. On a scheduled run that commit is the usual head of `main`, and skipping it would make the
  daily plan almost never run. The step skips only for `workflow_run` events.
- **The guard wait stays.** It looks for the push-event `guard` run on the planned commit. For `main`'s head that run
  has already finished, so the step passes at once, or fails if `guard` failed. That failure is worth seeing too.
- **Drift found.** The plan has changes, and the `apply` job waits for the owner's approval as any `main` run does.
  The run summary shows the plan. With no drift, the run ends after the plan and asks for nothing (ci-apply spec).
- **No new credential and no new environment.** The scheduled run uses exactly what a merge's run uses.

*Alternatives:*
- **A plan that only reports drift and fails, with no apply:** the owner would then start a manual run to restore the
  file, which is a second step for the same outcome. Rejected.
- **More often than daily:** each run with drift waits for the owner, and holds up later merges' runs while it waits.
  Daily keeps that to one a day. The cron is one line, so this can change later.
- **Option 2, refusing before the merge:** a check that runs from a copy the push can't change (a
  `pull_request_target` workflow, or one triggered from `main`), verifying that a commit touching a delivered file
  carries GitHub's own signature and the App's bot as author. It needs its own probe: whether a person can get GitHub
  to sign an API commit with a custom author isn't known. The owner chose to make it a follow-up issue (task 4.3).

**The spec text for this path.** If the probe rules out the ruleset, task 1.5 deletes `specs/rulesets/spec.md`,
replaces `specs/guard-delivery/spec.md` with the first block below, and adds `specs/ci-apply/spec.md` with the
second.

`specs/guard-delivery/spec.md`:

```markdown
# Spec Delta

## MODIFIED Requirements

### Requirement: Delivered files are changed only at their source
In a governed repository that receives delivered files, a commit that changes a delivered file SHALL be refused, and
an agent's edit to one SHALL be refused. The guard's GitHub check SHALL fail on a commit that changes a delivered file
unless its author is the App. A commit's author is self-declared, so a change that gets past these SHALL show in a
plan of `main` within a day, and an apply SHALL restore the file. The fix SHALL be to change the file in this
repository.

#### Scenario: Committing a change to a delivered file
- **WHEN** a contributor in `troupe` commits a change to `.githooks/pre-commit`
- **THEN** the commit is refused, naming the rule and saying to change the file in `troupe-run/infrastructure`

#### Scenario: An agent edits a delivered file
- **WHEN** an agent in a Claude Code session in `troupe` edits `scripts/guard.py`
- **THEN** the edit is refused, naming the rule and the source repository

#### Scenario: A pushed change to a delivered file
- **WHEN** a branch is pushed to `troupe` carrying a commit, not made by the App, that changes a delivered file
- **THEN** the guard's GitHub check for that push fails and names the commit and the file

#### Scenario: A forged delivery author shows within a day
- **WHEN** a commit that changes a delivered file, with the App's bot email written in as its author, reaches
  `troupe`'s `main`
- **THEN** a plan of `main` within a day shows the file returning to its source content, and applying it restores
  that content

#### Scenario: A delivery passes the check
- **WHEN** the App's delivery commit is pushed to `troupe`'s `main`
- **THEN** the guard's GitHub check passes

#### Scenario: The source repository edits its own files
- **WHEN** a contributor in this repository commits a change to `scripts/guard.py` on a change's branch
- **THEN** this rule does not apply
```

`specs/ci-apply/spec.md`:

```markdown
# Spec Delta

## ADDED Requirements

### Requirement: Main is planned every day
CI SHALL plan `main` once a day, whether or not anything merged. The plan SHALL be shown, and a plan with changes
SHALL wait for the owner's approval and apply as any plan of `main` does. A plan with no changes SHALL end the run
without asking for approval. The daily plan SHALL run whatever commit `main`'s head is, the App's state commit
included.

#### Scenario: Drift shows within a day
- **WHEN** a managed file or setting is changed on GitHub outside a delivery or an apply, and nothing merges
  afterwards
- **THEN** within a day, a run on `main` shows a plan restoring it and waits for the owner's approval

#### Scenario: The state commit is planned too
- **WHEN** the daily plan runs and `main`'s head is the App's state commit after an apply
- **THEN** the run plans `main` rather than skipping

#### Scenario: No drift asks nothing
- **WHEN** the daily plan finds the declaration and the org in agreement
- **THEN** the run ends after the plan, with no approval requested
```

## Risks / Trade-offs

- **[The probe says push rulesets work on a public repository, but GitHub later restricts them to paid plans]** →
  The ruleset's API calls would then fail, or it would be deactivated. Either shows in the next plan. The guard's
  author check still catches honest mistakes meanwhile.
- **[Push rules cover the fork network]** → A fork of `troupe` can't push a change to a delivered file either. That
  is intended: such a change belongs in this repository. A contributor sees GitHub's refusal and the ruleset's name.
- **[The `guard` check still runs the pushed copy of itself]** → The ruleset covers the delivered-file rule, because
  a push that changes `guard.py` or `guard.yml` is now refused before it can run. Other rules the `guard` check
  enforces (Conventional Commits, branch names) rest on required checks and review, as before. Out of scope here.
- **[Fallback path: GitHub turns off a public repository's scheduled workflows after 60 days with no activity]** →
  The next commit doesn't turn it back on; it has to be re-enabled in the Actions tab or with `gh workflow enable`.
  The README says so. Every merge here already plans `main`, so the gap only opens in a quiet repository.
- **[Fallback path: a scheduled run can start late when GitHub is busy]** → "Within a day" is the bound the docs
  promise, not to the minute.
- **[Fallback path: a forged edit is live until the owner approves the restoring apply]** → Known gaps says so:
  up to a day to show, then as long as the approval waits.
- **[The App's key is the trust root]** → Unchanged. The App already holds org administration and bypasses
  `protect main` in `troupe`.

## Migration Plan

1. The probe (D1), on a throwaway repository only. Its result picks the path (task 1.5).
2. **Ruleset path:** a pull request adding the module support and `troupe`'s `delivered_paths`. Its CI plan shows one
   ruleset added to `troupe` and nothing else. **Fallback path:** a pull request adding the schedule to `tofu.yml`.
   `scripts/plan_needed.py` doesn't list `.github/workflows/` as never read, so it is planned like any other, and the
   plan shows no changes.
3. After the merge, the owner approves the `main` plan if it has changes, and CI applies it.
4. **Ruleset path:** verify on `troupe` by reading the ruleset: the delivered paths, and the App as the only bypass.
   The refusals are shown by the probe, because GitHub behaviour isn't tested on a live repository. **Fallback
   path:** the first scheduled run is found with `gh run list --event schedule` and plans `main`.

**Rollback:** ruleset path: set `delivered_paths` back to `[]` (or revert the pull request), and the next plan deletes
the ruleset. Deliveries never depended on it. Fallback path: remove the `schedule` trigger.
