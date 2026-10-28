# Proposal

## Why

Since #194, only the review resolves a must-fix, and the review runs only when a pull request is opened or pushed to.
A must-fix answered with a reply alone stays open, and blocks the merge, until someone re-runs the last `claude review`
run by hand (#208). Judging the reply when it's posted takes that step away, and in infrastructure it saves the push
that would ask for the plan's approval again.

## What Changes

- The `claude review` workflow also starts on `pull_request_review_comment` (`created`). A run starts the same full
  review a push does, with the same prompt and jobs, so the reply is judged with the rest of the pull request (design
  D1).
- It runs for a reply to one of the review's open must-fixes only, by a person with write access to the repository,
  on a pull request from one of the repository's own branches. A bot's comment, the review's own findings and re-tier
  replies included, starts nothing; nor does an outside user's comment, a new comment that opens a conversation, or a
  reply to a nit, a decision or a person's conversation (design D2). A gate job, outside the concurrency group, reads
  the conversation replied to and decides, so a reply to a nit costs no Claude run and cancels nothing (design D2a,
  owner 2026-10-28).
- A run that's skipped can't cancel a review that's running. The review posts its findings while it runs, and each one
  starts a run that's skipped; with the concurrency group as it is, that run would cancel the review posting it. The
  group moves to the jobs, which a skipped job never joins (design D3).
- A reply still replaces a review running for the same pull request, as a push does, and a burst of replies collapses
  into the last one's run.
- Re-running the last run by hand stays possible, and stays the way when a run failed. The docs stop telling people to
  do it after a reply: `docs/development-workflow.md`, `org-profile/CONTRIBUTING.md`, `CLAUDE.md` and the context in
  `openspec/config.yaml`.
- `scripts/tests/test_claude_review_workflow.py` pins the new event, the reply-only skip and the job-level concurrency,
  and refuses `pull_request_review` and `issue_comment` triggers.
- A probe on a throwaway `infra-probe-*` repository shows, before anything depends on it: a reply starts a review that
  judges it, a bot's comment starts nothing and cancels nothing, an outside user's comment and a fork's reply start
  nothing, and a fork's run gets no secrets.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pr-review`: the review also runs when a person replies in one of a pull request's review conversations; who and
  what starts it, and that a skipped run can't cancel a running review. The weakened-workflow scenario covers the new
  trigger and its skip.

## Impact

- `.github/workflows/claude-review.yml`, delivered to troupe and website with the guard's files, so the change reaches
  them through a delivery plan the owner approves (spec: guard-delivery).
- `scripts/tests/test_claude_review_workflow.py`.
- Docs: `docs/development-workflow.md`, `org-profile/CONTRIBUTING.md` (written to troupe-run/.github by the apply),
  `CLAUDE.md`, `openspec/config.yaml`. troupe's and website's `config.yaml` don't mention re-running, so nothing changes
  there.
- Cost: a reply to a must-fix costs a full Claude review run, as a push does; a reply to a nit, which agents post
  before resolving each one, costs only the gate's few seconds. A narrower run that judges only the conversation
  replied to is cheaper, but needs its own prompt, its own tests and its own concurrency; it stays a follow-up if the
  cost shows (design D1).
- The Actions list gains a skipped run for each comment the review posts.
