# Proposal

## Why

CI runs this repository's tests more often than the code changes. A merge through the queue runs every leg on the
group's commit, and then the push of that same commit to `main` runs them all again, about 10 minutes before the plan
of `main` can start. On a pull request, the legs run alongside Claude's review, so when the review finds something,
they ran on code that's about to change. Decision #227 (owner, 2026-10-30) settles both: CI runs the matrix once for
each version of the code that matters. This repository goes first (#232, under Epic #231), because it writes the
draft-then-ready step that agents in every repository follow.

## What Changes

- **No second run on `main`.** On a push to `main`, CI asks GitHub whether its own merge-queue run already passed
  that exact commit. If it did, the `check` job and the guard-tests legs are skipped, `guard tests` reports success,
  and the run ends in success, so `tofu.yml`'s plan of `main` (and then the apply) starts as it does today. A commit
  the queue didn't pass, or one whose queue run can't be read, runs everything, as today.
- **Drafts run no legs and ask for no plan.** On a draft pull request, CI's `check` and legs are skipped, and
  `tofu.yml`'s `plan (pull request)` is skipped without asking the owner for an approval. Both workflows run on
  `ready_for_review`, so marking the pull request ready runs the legs and asks for the plan.
- **Marking a draft ready doesn't start another review.** `claude-review.yml` stops triggering on
  `ready_for_review` (owner, 2026-10-30, while proposing this change). Every push is still reviewed, before and after
  ready, so only the review of a head that was already reviewed clean is dropped. The file is delivered with the
  guard, so the change reaches troupe and website with this pull request's plan.
- **The draft-then-ready step is documented.** `docs/development-workflow.md`, CLAUDE.md's summary, and the org's
  contributing guide (`org-profile/CONTRIBUTING.md`) say a pull request opens as a draft, the review's findings are
  acted on, and it's marked ready once the review of its last push has nothing left to fix. It's a documented step,
  not a guard rule: marking ready early only costs runs, since a draft can't merge or join the queue, and the ruleset
  still blocks a merge with unresolved conversations.
- **The guard already allows both commands.** `gh pr create --draft` and `gh pr ready <n>` are everyday writes the
  guard allows and grants (`GH_WORKFLOW_WRITES`). This change checks them on the guard as it stands and changes a
  rule only if either is refused.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: CI's tests run once per pull request update that's ready for review, and once per commit on `main`
  that the merge queue didn't already pass; a draft isn't tested or planned until it's marked ready.
- `pr-review`: marking a draft ready no longer starts a review; opening, reopening and each push still do.
- `development-workflow`: a pull request opens as a draft and is marked ready once the review of its last push has
  nothing left to fix, as a documented step.

## Impact

- `.github/workflows/ci.yml`: the `changes` job also runs on a push to `main` and on drafts; `ready_for_review`
  joins its `pull_request` types. A new standard-library script answers whether the merge queue passed a commit, with
  tests. `scripts/tests/test_ci_workflow.py`'s pins change with it.
- `.github/workflows/tofu.yml`: `ready_for_review` joins its `pull_request` types, and its `changes` job answers "no
  plan" on a draft. Its tests change with it.
- `.github/workflows/claude-review.yml` and `scripts/tests/test_claude_review_workflow.py`: `ready_for_review` is
  dropped. The plan shows the file's delivery to troupe and website.
- `docs/development-workflow.md`, `CLAUDE.md`, `org-profile/CONTRIBUTING.md`. The contributing guide reaches
  `troupe-run/.github` through the plan the owner approves.
- Unchanged: `scripts/main_ci.py` and the scheduled and manual plans, which read CI's run on `main` as a whole and
  find it green; the merge queue's own run, which still runs everything; the `guard` check's triggers.
- Follows in other repositories: troupe-run/troupe#204 and troupe-run/website#77 change their own `ci.yml` and
  CLAUDE.md.
