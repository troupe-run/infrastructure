# Design: auto-merge

## Context

See proposal.md for why. #319 decided the safe-PR rule, the mechanism (a workflow queues through an App), the audit,
the switches and the rollout. #320 builds it. #275 adds the guard's blocked-by rule, which auto-merge also checks.
The draft design was posted on #320 (https://github.com/troupe-run/infrastructure/issues/320#issuecomment-7007532497)
and the owner answered its questions on 2026-11-19 (below).

What already exists and is reused:
- **The merge queue.** Every repository merges through a merge queue, rebase only. The queue runs the required checks
  again on the group, including `guard`. GitHub won't queue a pull request whose required checks haven't passed.
- **The quality gates** (`scripts/quality_gates.py`, spec: quality-gates). They already measure lizard complexity of
  changed functions against a base. The blocking threshold is 25. Auto-merge uses the same measure with stricter
  limits.
- **The guard** (`scripts/guard.py`). It reads a pull request's closing lines (`CLOSING`) for `pr-closes-issue`, and
  runs on every pull request and merge group in all three repositories.
- **The dispatch pattern.** `dependabot-issues.yml` runs on infrastructure's `main` with a narrow App, and troupe and
  website start it through the delivered `dependabot-dispatch.yml` with the `troupe-run-dispatch` App.
- **The review** (`claude-review.yml`). Its `completed` job already computes coverage (`complete`, `incomplete` or
  `unknown`) and a source-and-test floor. Only the floor gates the check today (#282, until #280).

## Goals / Non-Goals

**Goals:**
- queue exactly the pull requests #319's rule admits, with every setting in one config file;
- never run a pull request's code with the App's key;
- leave the owner a switch per repository, a per-pull-request hold and a full record of each decision;
- a week of dry-run before anything is queued.

**Non-Goals:**
- Dependabot's light path (#170, #301) stays as it is: a bot's pull request has no review, so it never qualifies.
- Carrying review coverage forward in general is #280; here only #319's `openspec/`-only carve-out.
- Merging remains owner-only for Claude sessions. The guard's `owner-only` merge rule is unchanged.

## Owner's decisions (2026-11-19, through the orchestrator)

- **Q1, limits:** "the recommended bracket: 800 changed code lines (lock files, fixtures, openspec/, docs/ and *.md
  left out), 30 files, max CCN 15 per new or changed function, total CCN increase 40. Keep the limits in config, as one
  source of truth." The evidence is under Calibration.
- **Q2, identity:** "a new narrow App, troupe-run-merge (contents and PR write, issues read), key only in
  infrastructure's auto-merge environment, main only." This replaces #319's naming of `troupe-run-infrastructure`.
  That App administers the org, and its key would otherwise have sat in an unattended environment.
- **Q3, switch:** "an AUTO_MERGE variable (off | dry-run | on; unset = off; anything else is an error), dry-run for a
  week, then on."
- **Q4, dry-run reporting:** "one 'would have queued' comment per head SHA."
- **Additions, all confirmed:**
  - "hold removal owner-only";
  - "never re-queue a removed head";
  - "fork PRs never qualify";
  - "any open blocker counts, and an unreadable dependency fails".

## Decisions

### D1. One evaluator, in infrastructure, judging every open pull request

`.github/workflows/auto-merge.yml` runs `scripts/auto_merge.py` on infrastructure's `main`, in the `auto-merge`
environment, the only place the merge App's key exists. Each run lists the open pull requests of troupe,
infrastructure and website and judges each one. A run carries no inputs, so a dispatcher can't steer it.

It's started by:
- in infrastructure: `workflow_run` of CI, guard and claude review (completed), and `pull_request_target` of
  `labeled` and `unlabeled`;
- in troupe and website: the dispatcher (D8);
- everywhere: a backstop schedule (`*/15 * * * *`), because resolving a conversation, DCO's check and the queue's
  outcome start no workflow, and schedules here run late (memory: drift-schedule-runs-late);
- `workflow_dispatch` (the dispatcher's way in, and the owner's).

Concurrency: one group, `cancel-in-progress: false`, so a burst ends with one run that starts after the last event.

*Alternatives:*
- *A copy of the workflow in each repository:* the key would be in three repositories. #319's "delivered to all
  three" is met by the delivered dispatcher instead.
- *Judging only the pull request the event names:* the dispatcher would have to pass the event's data, which its spec
  forbids. A full sweep costs a few API calls per open pull request. There are rarely more than 20.

### D2. What a run reads, and from where

Everything is read through the API as the App, or as git data:
- pull request fields;
- `rules/branches/main` for the required checks;
- check runs on the head;
- `reviewThreads` and `reviewDecision` (GraphQL);
- commit messages;
- the tree at head (for `openspec/changes/<branch>/`);
- closing issues: the `CLOSING` lines of the description, together with GraphQL `closingIssuesReferences`, then each
  issue's type, labels and `dependencies/blocked_by`;
- the variable `AUTO_MERGE`;
- the review's `review-result` artifact (D6).

For size and complexity it fetches `refs/pull/<n>/head` into a blobless clone and runs `quality_gates`' diff and
lizard functions on the base and the head. lizard parses files; nothing from the pull request is executed.

### D3. The rule's order and its result

The conditions are checked cheapest first:
1. the switch;
2. open, not a draft, base `main`, same-repository head, no `hold`, no conflict;
3. queued before on this head (D5);
4. required checks;
5. conversations and requested changes;
6. sign-off and archive;
7. closed issues;
8. protected paths;
9. size and complexity;
10. the review result.

The first failure ends the judging of that pull request. The run summary has one line per pull request: qualified,
or the first failing condition with what it saw. Errors (an unreadable read, a malformed variable) are a failure of
that pull request's judging, never a pass, and the run exits non-zero if any happened, so the schedule watch's red
shows up.

### D4. `auto-merge.toml`

```toml
version = 1

[defaults]
max_lines = 800
max_files = 30
max_function_complexity = 15
max_complexity_increase = 40
generated = ["**/uv.lock", "**/package-lock.json", "**/fixtures/**"]
prose = ["openspec/**", "docs/**", "**/*.md"]
protected = [".github/**", ".githooks/**", ".claude/**", "scripts/guard.py", "scripts/guard_pytest.py",
             "scripts/quality_gates.py", "quality-gates.toml", "release-please-config.json",
             ".release-please-manifest.json"]
complexity_exclude = ["**/tests/**", "**/test_*.py"]
languages = ["python", "typescript", "javascript"]

[repositories.infrastructure]
protected = ["tofu/**", "oob/**", "org-profile/**", "auto-merge.toml", "scripts/auto_merge*.py"]

[repositories.troupe]
protected = ["**/*masking*.py", "**/*credential*.py", "**/masking_checks.py"]

[repositories.website]
```

A repository's `protected` adds to the defaults' and never replaces them. Its limits, when given, replace the
defaults' for that repository. Every path in the repository's own `.github/guard-delivery.json` at `main` is
protected as well, though `.github/**` already covers that file. Deleting a `pyproject.toml`, a `package.json` or an
`openspec/specs/*/spec.md` counts as deleting a component.

The file is read strictly, as `quality-gates.toml` is: an unknown key, a wrong type or a negative limit fails the
run. The config is in infrastructure, not delivered, because only the evaluator reads it.

### D5. Queueing, once per head, and taking out on hold

- **Queue:** GraphQL `enqueuePullRequest(pullRequestId, expectedHeadOid: <judged head>)`. A push since the judging
  makes GitHub refuse it. Then the `auto-merged` label, and a comment that starts with the marker
  `<!-- auto-merge:queued <sha> -->`.
- **Once per head:** a pull request whose comments include the App's `queued` marker for its current head is never
  queued again, wherever it is now. Leaving the queue (the owner's removal, a failed group, the runner-capacity drop)
  doesn't reset it. A new push does, because the head changes.
- **Hold:** an open pull request with `hold`, that's in the queue and has the App's `queued` marker for its head, is
  taken out with `dequeuePullRequest`. One the owner queued by hand is the owner's, and is left alone.
- **Dry-run:** the same comment with `<!-- auto-merge:dry-run <sha> -->` and "would have queued". It's posted only
  if no comment with that marker exists.
- Only comments written by `troupe-run-merge[bot]` count as markers. Anyone can write the text, but GitHub records
  who wrote it.

*Alternative:* `enablePullRequestAutoMerge`. It waits for checks and can arm a merge that lands later. On a blocked
pull request it arms SQUASH, which never queues (memory: review-conversation-findings). Direct queueing of a pull
request already judged green avoids both.

### D6. The review result artifact

The `completed` job of `claude-review.yml` writes `review-result.json`, `{"head": sha, "coverage": ..., "code": ...}`,
from the values it already computes, and uploads it as the artifact `review-result` (retention 30 days), before it
decides the check. The evaluator finds the newest `claude review` run of event `pull_request` for the SHA, reads the
artifact and requires `head` to match and `coverage == "complete"`.

The carve-out (#319: "or on the last commit that changed code when only openspec/ has changed since"): walk back from
the head through the pull request's commits while each changes only `openspec/` paths. The first commit with a
`complete` result ends the walk and counts. A commit that changes anything else ends the walk with the condition
failed.

The workflow is delivered, so troupe and website get the artifact with the next delivery. Until then a pull request
there has no result, and isn't queued.

### D7. The guard's `blocked-by` rule

The new rule id is `blocked-by`, not overridable: like `openspec-strict`, it's only checked on GitHub, where no
override is consumed. It's part of `guard.py ci` after the git-level rules.
- **Pull request:** the closed issues come from the description, with the same `CLOSING` pattern as
  `pr-closes-issue`, resolved against `GITHUB_REPOSITORY` for `#n`.
- **Merge group:** the pull request number comes from the group's `head_ref`
  (`refs/heads/gh-readonly-queue/main/pr-<n>-<sha>`), then the description from `GET pulls/<n>`. A head_ref of
  another shape fails the rule.
- **Push:** nothing to check.
- For each closed issue: `GET repos/<o>/<r>/issues/<n>/dependencies/blocked_by`, and each blocker's `state`. An open
  blocker fails, with the message #275 asked for. Anything unreadable fails (owner, 2026-11-19).
- A release pull request exempt from `pr-closes-issue` closes nothing, so it passes.

Token: `github.token`, with `issues: read` and `pull-requests: read` added to `guard.yml`. All three repositories are
public, so the token can read another repository's issues. Task 1.1 probes this on an `infra-probe-*` repository
before anything depends on it. If it can't, the fallback is the merge App's token, which would need a decision,
because it moves the key.

Re-checking: a blocker closing doesn't re-run `guard`. The merge group re-checks, the evaluator checks blockers
itself before queueing, and a red check is re-run with `gh run rerun`.

### D8. The dispatcher

`dependabot-dispatch.yml` gets a second job, `start auto-merge`. It runs on `workflow_run` of `CI`, `guard` and
`claude review` (completed) and `pull_request_target` (`labeled`, `unlabeled`), skipped in infrastructure. It runs
`gh workflow run auto-merge.yml -R troupe-run/infrastructure --ref main` with the dispatch App's token, which already
has exactly this permission. The existing job gains `if:` on the triggering workflow's name, so each job starts only
its own workflow. Nothing from the event is passed. The only expressions that read the event choose the job.

### D9. The guard: lifting a hold is the owner's

- `gh pr edit` and `gh issue edit` with `--remove-label` naming `hold` (alone or in a comma list, in any case) are
  refused under `owner-only`.
- `DELETE .../issues/<n>/labels/hold`, and the label-set endpoints, are already off the allow-list (one way per
  write).
- GraphQL `removeLabelsFromLabelable` and `clearLabelsFromLabelable` are already refused as unlisted mutations.
- A test pins each route.

### D10. The merge App and its environment

The `troupe-run-merge` App, created by the owner:
- **Repository permissions:**
  - pull requests: write (comment, label, queue, dequeue);
  - contents: write. The owner listed it. Task 1.2 probes whether `merge_queues: write` alone queues; contents write
    is kept only if it's needed;
  - issues: read (closed issues, their types and dependencies);
  - checks: read;
  - actions: read (the review artifact);
  - variables: read (`AUTO_MERGE`);
  - metadata: read.
- **Organisation permissions:** none.
- **Events:** none (no webhook).
- **Installation:** selected repositories troupe, infrastructure and website.

Task 1.2 trims anything the probe shows isn't needed before the declaration in `oob/app-installations.json` is
written. The environment `auto-merge` on infrastructure is main-only, with no reviewers and no admin bypass, and holds
`MERGE_APP_PRIVATE_KEY` (secret) and `MERGE_APP_CLIENT_ID` (variable), as `dependabot-issues` does. It's added to
`scripts/tests/test_main_only_environments.py`.

### D11. Labels and variables in OpenTofu

- `hold` and `auto-merged` join `tofu/labels/workflow.json`, so every managed repository gets them.
- `AUTO_MERGE` is a `github_actions_variable` in each of the three repositories, `dry-run` at first.
- Switching to `on` is a later pull request after the dry-run week, so it's the owner's approved plan, not a hand
  edit.

## Calibration (evidence for Q1)

Sample: the last 120 merged pull requests in troupe and infrastructure, and all 62 in website, taken on 2026-11-19.

"Eligible" means two things:
- **not Dependabot's:** its pull requests have no review, so they're out regardless;
- **touching nothing protected:** the list in D4, plus deletions of a component.

Lines leave out lock files, fixtures, `openspec/`, `docs/` and `*.md`. Complexity is lizard on non-test `.py`, `.ts`
and `.js` files, changed functions only. Each cell is the number of pull requests that would have auto-merged, as a
percentage of all and of eligible:

| repo | all | dependabot | protected | eligible | tighter 400/15/10/+20 | **chosen 800/30/15/+40** | looser 1500/50/20/+80 |
|---|---|---|---|---|---|---|---|
| troupe | 120 | 18 | 30 | 72 | 35 (29% / 49%) | 47 (39% / 65%) | 56 (47% / 78%) |
| infrastructure | 120 | 18 | 97 | 5 | 3 (2% / 60%) | 5 (4% / 100%) | 5 (4% / 100%) |
| website | 62 | 20 | 14 | 28 | 15 (24% / 54%) | 22 (35% / 79%) | 26 (42% / 93%) |
| overall | 302 | 56 | 141 | 105 | 53 (18% / 50%) | 74 (25% / 70%) | 87 (29% / 83%) |

Only size, complexity and the protected list are modelled. Some of these pull requests had review coverage only at
the floor, so the real rates are somewhat lower. The dry-run week measures them.

Distributions over eligible pull requests (p50 / p75 / p90):

| measure | troupe | website |
|---|---|---|
| changed code lines | 282 / 911 / 1609 | 103 / 242 / 565 |
| changed files | 14 / 36 / 51 | 13 / 19 / 28 |
| max function complexity | 7 / 17 / 32 | 0 / 7 / 14 |
| total complexity increase | 2 / 38 / 108 | 0 / 5 / 42 |

## Risks / Trade-offs

- **[A wrong rule merges something unsafe]** → a week of dry-run first, each condition tested against recorded
  pull-request shapes, the merge group's checks still run, and `hold` and `AUTO_MERGE=off` stop it at once.
- **[The App's key leaks]** → it can queue and comment, not push, change settings or merge past the queue. Its key is
  in one main-only environment.
- **[An agent games a condition]** (for example, resolving conversations it shouldn't) → unchanged: agents can't
  resolve must-fixes or decisions (guard), and lifting `hold` becomes owner-only.
- **[A run errs in a loop every 15 minutes]** → it fails red, and the schedule watch reports a stopped schedule. A
  failure on one pull request doesn't stop the others being judged.
- **[GITHUB_TOKEN can't read another repository's issue dependencies]** → probed first (task 1.1). The fallback needs
  the owner's decision.
- **[Review result missing in troupe and website until the delivery]** → those pull requests aren't queued until
  then (fail-safe).
- **[Lizard measuring TypeScript or Astro differently]** → `.astro` isn't measured (lizard can't). Its lines still
  count toward the limit.

## Migration Plan

1. This pull request closes #275, and is "part of #320". It lands the rule, the evaluator, the guard's rules, the
   environment, the labels, and `AUTO_MERGE=dry-run` in all three repositories. The owner creates and installs the App
   and sets its key, then approves the plan.
2. The owner approves the delivery of the guard's files, the review workflow and the dispatcher to troupe and
   website.
3. A dry-run week: a tally of "would have queued" comments against what the owner then merged by hand, posted on
   #320.
4. A follow-up pull request sets `AUTO_MERGE=on` in all three (#319: "all three repositories at once") and closes
   #320.

**Rollback:** set `AUTO_MERGE=off` by plan, or by hand in the UI as break-glass. The evaluator then does nothing.

## Open Questions

None that change the specs or tasks. The App's final permission list waits on task 1.2's probe, within what the
owner approved.
