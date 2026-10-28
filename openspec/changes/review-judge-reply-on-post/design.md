# Design

## Context

`.github/workflows/claude-review.yml` runs on `pull_request` (`opened`, `synchronize`, `reopened`,
`ready_for_review`). It has two jobs: `review`, where Claude reads the conversations snapshot and posts findings with
the review App's read-only token, and `resolve`, which resolves and re-tiers what Claude named with a contents-write
token (archived `review-findings-by-severity`, D3 to D4a). One workflow-level concurrency group per pull request,
`claude-review-<number>`, cancels a run in progress when a new one starts. The `review` job skips bots' pull requests
and forks' by `if:`. `scripts/tests/test_claude_review_workflow.py` pins all of it, including `on` being
`pull_request` only.

What the pinned action does on a review comment event (`anthropics/claude-code-action` at `925afb5`, read on
2026-10-28): `src/modes/detector.ts` picks agent mode for a `pull_request_review_comment` event when a `prompt` is
given, as it does for `pull_request`, so no `@claude` trigger phrase is needed. Before it runs, it checks the actor
(the commenter) is a `User`, not a bot (`checkHumanActor`), and has write access (`checkWritePermissions`), and fails
the step if not.

GitHub's docs say a `pull_request_review_comment` run checks out the pull request's merge ref, as `pull_request` does,
and a fork's run gets no secrets. The issue asks for both to be shown on a probe.

## Goals / Non-Goals

**Goals:**

- A person's reply in a review conversation is judged by a run that starts when it's posted.
- No comment the review posts, and no skipped run, can stop a review that's running.
- A reply that the review has nothing to do with, such as one to a nit, starts no Claude run.

**Non-Goals:**

- A narrower run that judges only the conversation replied to (D1).
- Starting on an edited or deleted comment, a submitted review's body (`pull_request_review`), or a top-level pull
  request comment (`issue_comment`). An edited reply is judged on the next reply, push or re-run.
- Changing the prompt, the tiers, or what the resolving job may do.

## Decisions

### D1. A reply starts the same full review a push does

The reply's run is the workflow as it is, with the same jobs and the same prompt: it reads every conversation, judges
the reply with the rest, and reviews the head again.

- **Alternative: a narrower run** that reads only the conversation replied to and decides resolve, re-tier or leave
  it. It costs less per reply. But it needs a second prompt, where the pr-review spec keeps the review's instructions
  in one place. It needs its own tests, and its own concurrency group, since a narrow run in the review's group would
  cancel a full review of a push, and a narrow run outside it could resolve a conversation while a full review is
  deciding about it.
- **Cost:** a full Claude run per reply that D2a lets through: a reply to one of the review's open must-fixes. A
  burst of them collapses into one run (D3). A narrow run is a follow-up if the cost shows.

The owner chose this with D2a (2026-10-28), after a side agent pointed out the cost without it: agents reply to every
nit before resolving it, with the owner's login, so each batch of nit replies would end in a full review that judges
nothing.

### D2. The review job runs for a person's reply only

The first job's `if:` (the gate's, D2a) keeps today's skip for every event, and adds, for a review comment:

```yaml
if: >-
  github.event.pull_request.user.type != 'Bot'
  && github.event.pull_request.head.repo.full_name == github.repository
  && (github.event_name == 'pull_request'
      || (github.event.comment.in_reply_to_id != null
          && github.event.comment.user.type != 'Bot'))
```

The trigger is `pull_request_review_comment: types: [created]`.

- **Reply only** (`in_reply_to_id`): a reply answers a conversation, which is what the review judges. A new comment
  that opens a conversation is a person's own, which the review never resolves, so it can wait for the next push.
- **Not a bot**: the review's own findings and re-tier replies are posted with an App token, and an App token's events
  start workflows (a `GITHUB_TOKEN`'s don't). Without the skip, each finding would start another review.
- **Write access is asked, not read from the comment.** Anyone can comment on a public repository's pull request. The
  design first skipped by the comment's `author_association` (`OWNER`, `MEMBER`, `COLLABORATOR`), but the probe showed
  the owner's reply carries `CONTRIBUTOR`: troupe-run's memberships are private, and GitHub then labels a member as
  any past contributor (Probe results). So the gate's step asks GitHub for the commenter's permission on the
  repository (`repos/<repo>/collaborators/<login>/permission`) and says no unless it's `admin` or `write`, which is
  how that API reports maintain too. An outsider's reply costs the gate's few seconds and no Claude run, and its run
  doesn't fail. The action's own write check stays behind it (owner, 2026-10-28).
- **The pull request's own skip** stays first, so a fork's pull request and a bot's are skipped whatever the comment.

`resolve` needs `review`, so it's skipped with it.

### D2a. A gate job lets through only a reply to an open must-fix of the review's

Only a must-fix is the review's to resolve, and only a must-fix's reply changes what it does. A nit is the author's,
and the docs have the author reply to every nit before resolving it; a decision is the owner's. Agents post those
replies with the owner's login, so D2's skip lets them through. Without more, each batch of nit replies ends in a full
review that judges nothing (owner, 2026-10-28).

So a job `gate` runs first, with D2's `if:`, and decides. For a `pull_request` event it says yes without reading
anything. For a review comment it mints the review App's token read-only (contents read, pull requests read), asks
the commenter's permission (D2), then reads the pull request's review conversations with the same query as the snapshot step, and finds the one whose comments
hold the comment replied to (`in_reply_to_id`). It says yes only when that conversation is open, the review App opened
it, and its tier, the review's latest label in it, is must-fix. `review` needs `gate` and runs only on its yes.

- **The gate has no concurrency group.** A step inside `review` can't decide this: by the time it runs, the job has
  joined the group and cancelled the review that's running. The gate is outside the group, so a no costs a few
  seconds and cancels nothing.
- **A read that fails fails the gate**, saying so, and no review starts (a malformed answer is an error, not a no).
  Re-running the run judges the reply.
- **The tier and the bot are read as the resolving step reads them**: its `LABEL` and `BOT` are copied into the gate,
  and the tests hold the copies equal, as they do the resolver's and the guard's.
- **Alternative: agents batch their nit replies, or post them just before a push.** It narrows the cost but doesn't
  remove it, and it's a convention no check enforces.

### D3. The concurrency group moves to the jobs

Each comment the review posts starts a run, skipped by D2. With the group at the workflow level, that run joins the
group as soon as it's queued, before any `if:` is read, and cancels the review that posted the comment. So the group
moves onto both jobs:

```yaml
concurrency:
  group: claude-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true
```

A job whose `if:` is false is expected to be skipped without joining its group, so only a run that reviews can
cancel one. That's an expectation, not something read in GitHub's docs, and the probe checks it (D4). Both jobs
share the group: a new review cancels an earlier run's review or its resolving job, as the workflow-level group did,
and a run's own `resolve` waits on its `review` through `needs`, so it never races it.

- **Alternative: keep the workflow-level group, with a unique name for a run that will skip** (the run's ID appended
  when D2's condition is false). It works, but it repeats D2's condition in a second expression that has to be kept
  equal to the first. It's the fallback if the probe shows a skipped job joins a job-level group.

### D4. The probe stands in for Claude

The probe repository, `troupe-run/infra-probe-review-reply`, is public and has its own workflow with this design's
trigger, `if:`, gate (D2a, its step as written for the review workflow) and concurrency, and a job that sleeps and
reports whether a probe secret is set, standing in for Claude. That shows the GitHub behaviour (what starts, what's
skipped, what's cancelled, what a fork's run gets, which ref is checked out, which association the owner's reply
carries, and what the gate lets through) without the org's Claude token, which isn't visible to the probe. The review
App is installed on the probe for the probe's length, as in #194's probe: it posts the bot's comments, and the gate
mints its token with the App's key, which the owner sets as a repository secret on the probe from 1Password.

That Claude then judges a reply is shown on this change's own pull request: a `pull_request_review_comment` run uses
the workflow from the pull request's merge ref, so a reply to one of the review's findings there runs this change's
workflow. The run and its outcome are recorded as evidence in `tasks.md`.

### D5. The docs say a reply is judged, and keep the re-run for a failed run

`docs/development-workflow.md`'s "The review runs on each push, not on a reply" becomes "The review runs on each push
and each reply"; a re-run (`gh run rerun <id>`) stays as the way to judge again after a run that failed or was
skipped. `org-profile/CONTRIBUTING.md`, `CLAUDE.md` step 5 and `openspec/config.yaml`'s context lose the instruction
to re-run after a reply.

## Risks / Trade-offs

- [A reply to a must-fix costs a full review] → D1; D2a keeps nit and decision replies out; the concurrency group
  collapses bursts; a narrow run is a follow-up.
- [The gate reads the conversations a moment before the review does, and the tier changes in between] → The review
  reads them afresh and judges what it finds; at worst a review runs that a later reading wouldn't have started.
- [A reply cancels a push's review part-way, after it posted some findings] → The reply's run reads them in its
  snapshot and doesn't post them again. Today a second push does the same.
- [A pull request's text, or a reply, injects instructions] → Unchanged: the review already reads every reply, and a
  reply now reaches it sooner. Only people with write access start a run, and the tools and tokens are the same.
- [The Actions list fills with skipped runs, one per comment the review posts] → Accepted; they cost no runner time.
- [The job-level group behaves differently from the docs] → The probe (D4) checks a skipped job cancels nothing
  before the workflow depends on it; D3's alternative is the fallback.

## Migration Plan

1. Probe on `troupe-run/infra-probe-review-reply` (D4), then delete it and remove the review App from it.
2. The workflow, its tests and the docs, in this change's pull request; Claude's judging of a reply is shown there.
3. With the workflow in place, run website's `npx vitest run tests/unit/workflow-node-version.test.ts` and troupe's
   `uv run scripts/check.py` (the workflow's header), since the merge's apply delivers it to both.
4. After the merge, the owner approves the plan that delivers it to troupe and website, and writes CONTRIBUTING.md to
   troupe-run/.github.
5. Rollback: drop the `pull_request_review_comment` trigger. Re-running by hand works as it did before.
