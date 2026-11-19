# Proposal: auto-merge

## Why

Every pull request in troupe-run waits for the owner to queue it, though most of the 10–20 a day have already passed
every check by then. #319 (owner, 2026-11-17) decided which pull requests are safe enough to merge without the owner,
and that a workflow queues them through a GitHub App. #320 builds that. A pull request whose closed issue is blocked
by an open issue must never be one of them, and today nothing stops such a merge at all: GitHub shows issue
dependencies but never enforces them. #275 builds that rule in the guard, and it lands here because auto-merge
relies on it.

## What Changes

- **The safe-PR rule** (#319, #320), evaluated by a new `scripts/auto_merge.py` against each open pull request in
  troupe, infrastructure and website. A pull request qualifies only when every condition holds:
  - it isn't a draft, isn't from a fork and has no `hold` label;
  - every required check is green on its head;
  - Claude's review read everything and no conversation is open;
  - every commit is signed off and its change is archived;
  - it closes no Decision, no `needs:owner` issue and no blocked issue;
  - it changes nothing on the protected list and is within the size and complexity limits.
- **One config file**, `auto-merge.toml`, holding the protected list and the limits, per repository, read strictly.
  Defaults, calibrated on the last 120 merged pull requests per repository and chosen by the owner (2026-11-19):
  800 changed code lines, 30 files, cyclomatic complexity 15 for any new or changed function, and a total increase
  of 40 (design, Calibration).
- **The evaluator** is `.github/workflows/auto-merge.yml` on infrastructure's `main`. It runs on this repository's CI,
  guard and review runs and its label changes, on a dispatch from troupe and website, and on a 15-minute backstop. It
  queues a qualifying pull request with GraphQL `enqueuePullRequest` and the head it judged, as a new narrow App,
  `troupe-run-merge`, whose key lives only in a main-only `auto-merge` environment (owner, 2026-11-19).
- **The switch.** A repository variable, `AUTO_MERGE`: `off`, `dry-run` or `on`. Unset means `off`, and anything else
  is an error. OpenTofu sets each repository to `dry-run` for a week, then `on` (owner, 2026-11-19).
- **Audit.** A queued pull request gets the `auto-merged` label and one comment naming the rule's version and what it
  saw. In dry-run it gets one "would have queued" comment per head and no label (owner, 2026-11-19).
- **What stops it:**
  - the `hold` label, which also takes a queued pull request out of the queue;
  - the switch;
  - a new push;
  - the merge group's checks;
  - and once per head: the App never queues a head SHA twice, so one the owner took out of the queue stays out.
- **Guard, `blocked-by` (#275).** On a pull request and in a merge group, `guard` fails while an issue the pull request
  closes is blocked by an issue that's still open, in any repository, naming the blocker and the fix. Every open
  blocker counts, and a dependency that can't be read fails the check (owner, 2026-11-19).
- **Guard, `hold` is the owner's to lift.** Removing the `hold` label from a pull request is added to the owner-only
  acts, so an agent can't release its own pull request.
- **Review result.** The review's `completed` job records its coverage for the head in a small artifact, so the
  evaluator can tell complete coverage from the floor.
- **Dispatcher.** The delivered `dependabot-dispatch.yml` also starts `auto-merge.yml` when CI, guard or the review
  completes in troupe or website, or a pull request's labels change there. It still passes nothing from the event.

## Capabilities

### New Capabilities

- `auto-merge`: which pull requests are queued without the owner, where the rule's settings live, how it's switched,
  what stops it, and what it records on the pull request.
- `merge-credentials`: the `troupe-run-merge` App, its installation and permissions, and the main-only environment
  that holds its key.

### Modified Capabilities

- `development-workflow`: the guard's new `blocked-by` rule on GitHub, and removing `hold` as an owner-only act.
- `dependency-updates`: the dispatcher in troupe and website also starts `auto-merge.yml`.
- `pr-review`: the `completed` job records the head's coverage for the evaluator to read.
- `labels`: every managed repository has `hold` and `auto-merged`.

## Impact

- New: `scripts/auto_merge.py` and its tests, `auto-merge.toml`, `.github/workflows/auto-merge.yml`,
  `tofu/auto_merge.tf` (environment, client ID variable, `AUTO_MERGE` variables), the App's `oob/` declaration and
  set-up notes.
- Changed:
  - `scripts/guard.py` and its tests;
  - `.github/workflows/guard.yml` (issues and pull requests read);
  - `.github/workflows/claude-review.yml`;
  - `.github/workflows/dependabot-dispatch.yml`;
  - `tofu/labels/workflow.json`;
  - `docs/development-workflow.md`;
  - `README.md`.
- The guard's files, the review workflow and the dispatcher reach troupe and website by a delivery the owner approves.
- Owner steps: create the `troupe-run-merge` App and install it on the three repositories, set its key in the
  `auto-merge` environment, approve the plan, and after the dry-run week, approve the plan that switches it `on`.
- Nothing changes for Claude sessions: merging stays owner-only.
