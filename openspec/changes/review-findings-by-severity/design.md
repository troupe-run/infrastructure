# Design

## Context

See proposal.md for why. Today the review (`.github/workflows/claude-review.yml`) posts inline comments with
`mcp__github_inline_comment__create_inline_comment` and a summary with `gh pr comment`. Nothing labels a finding's
severity, the review doesn't read its earlier comments, and no ruleset looks at conversations. Since #157 the review
has posted findings on 16 merged pull requests. Most of them are in summaries only: of those 16, 6 have any inline
comment, and #187 merged with its one inline finding unanswered.

The fences this design must keep:

- **The review can't change the repository.** Claude's tools are reading the pull request, posting inline comments,
  and `gh pr comment`. The review App's token holds `contents: read` and `pull_requests: write` only (spec: pr-review).
- **GitHub never tells an agent from the owner** (#47). They share one gh login. Agents are held back locally, by the
  guard.
- **One way per write.** Agents' everyday writes go through `gh`. GraphQL mutations are refused, and
  `GH_MUTATIONS_ALLOWED` is empty, kept for "a write gh can't do". Resolving a conversation is one: `gh` has no
  command for `resolveReviewThread`.
- The guard is standard library only, and its local hooks work offline, except where a command is itself online.

The owner's choices (2026-10-27, in the session that wrote this change): use GitHub's own conversation resolution
rather than a custom check. Keep every finding inline, where its context is. Three tiers named for who resolves:
must-fix (the review), nit (the author) and decision (the owner), in place of severity levels, since two levels that
are handled the same way are a distinction for nothing. Involve the owner only for decisions and disputes, and an
agent's reason alone doesn't clear a must-fix.

## Goals / Non-Goals

**Goals:**

- Nothing the review finds merges unanswered, and no must-fix merges until the review sees it addressed, or the
  owner decides.
- The owner sees only disputes and choices.
- No new tool for Claude, and no new permission for the review App.

**Non-Goals:**

- Making the review's run a required check, or making a merge wait for it (D7).
- Changing what the review checks (its five checks stay as they are).
- Resolving conversations that people open. Those stay with people.

## Decisions

### D1. The tier is a fixed label on the comment's first line

Each finding's comment starts with one line in a fixed form, which the guard and the workflow's resolving step both
parse:

```
**must-fix** · <one-line title>
**nit** · <one-line title>
**decision** · <one-line title>
```

The tiers are defined once, in the prompt, each by who resolves it:

- **must-fix:** someone other than the author should check the fix before it merges. Wrong behaviour, lost data, a
  weakened security fence, a missing test or one whose name claims more than its body checks, a ticked task with
  nothing behind it, or a pull request that doesn't do its issue's "Done when".
- **nit:** the worst outcome of leaving it is a reader briefly misled, or untidy code. Wording, a stale reference,
  style, a nice-to-have, or a cheap choice only this pull request's code depends on.
- **decision:** a choice between defensible options that the change's design doesn't settle, and that's hard to
  reverse or reaches beyond the pull request.

Unsure between must-fix and nit means must-fix: a must-fix mislabelled a nit is waved through by its author, while a
nit mislabelled a must-fix costs one re-review. Unsure whether it's a decision means decision, for the same reason.

**The tier follows the conversation.** A conversation's tier is the label on the latest comment in it by
`troupe-run-review[bot]`. The review re-tiers by replying with a new label line and its reason: up to decision when
the author's reply shows a real choice, down to nit when it shows the problem is small, or up to must-fix when a nit
turns out to matter. The author can't re-tier: a label in a reply from the owner's login counts for nothing, because
an agent's reply looks the same (#47), and a downgrade by the author would let it resolve its own must-fix. The owner
doesn't need to re-tier: they resolve, or reply, and the review reads the reply. When the review is convinced a
must-fix is addressed, it resolves it rather than downgrading it.

A conversation whose latest review comment has no label that parses counts as unlabelled. The guard treats it as not a nit, so an agent
can't resolve it. The step treats it as not a must-fix, so the review doesn't resolve it. Either way, it falls to the
owner, which is the choice that can't let something through.

The parser lives in `scripts/guard.py`, since the guard is delivered everywhere. The workflow's step has to be
self-contained (it's inline in the workflow, as the denial-report step is), so it carries its own copy. A test checks
that the two agree on a table of first lines, and that the prompt's examples parse.

*Alternatives:* GitHub's suggested-change or "review" severities don't exist. Labels on the pull request can't be
attached to one comment. A hidden HTML marker would be invisible to the reader, who needs to see the tier anyway.
Severity levels (critical, important, minor) were the first draft; important and critical were handled identically,
so they were folded into must-fix, and decision became a tier of its own rather than a flag on another (owner,
2026-10-27).

### D2. Every finding is a conversation

The prompt asks for every finding inline. A finding about the whole pull request goes on the line closest to what it
concerns: the task's line in `tasks.md`, the requirement in a delta spec, or the first changed line of the file it's
mainly about. The summary comment stays, as an index, and isn't a conversation.

The ruleset's `required_review_thread_resolution` then covers every finding, whoever it's for (spec: rulesets). It
also covers a person's own comments. With one maintainer, those are rare, and the owner resolves them.

### D3. The review reads earlier conversations from a file a step writes

A step before Claude, using the review App's token, runs `gh api graphql` with a paginated `reviewThreads` query and
writes the result to `.review-threads.json` in the workspace. For each conversation it records the ID, whether it's
resolved, its path and line, and each comment's author and body. Claude reads the file with Read, which it already
has.

The step fails the run if the query fails. Without it, Claude would post every open finding again and resolve
nothing.

*Alternatives:* giving Claude `gh api graphql` would let it send mutations too, because a tool pattern can't tell a
query from a mutation. `gh pr view --comments` doesn't return conversations' IDs or their resolved state.

### D4. The review names what it considers addressed, and a fixed step resolves it

Claude returns the IDs of the conversations it considers addressed as the action's structured output: `claude_args`
gets `--json-schema` with `{"resolve": [string], "retier": [...]}`, which the action exposes as
`steps.review.outputs.structured_output`.
A step after Claude, run with the App's token, resolves each ID only if it passes every check against the snapshot
from D3 (not against anything Claude says):

- the conversation exists on this pull request;
- it's unresolved;
- its first comment is by `troupe-run-review[bot]`;
- its tier, the label on the review App's latest comment in it, is must-fix.

Each ID that fails a check is named in the log as a warning. Resolved ones are listed. If an individual mutation
fails, the step warns and goes on to the next.

So prompt injection can make the review resolve at most its own must-fixes, which is what re-reviewing already lets
it judge. It can't reach a person's conversation, a nit (the author's), or a decision (the owner's).

The step's script is pinned by hash in `scripts/tests/test_claude_review_workflow.py`, like the denial report's. The
same test fails if the step runs with any other token, resolves without the snapshot checks, or if Claude's tool list
gains `gh api`.

**Re-tiering goes through the same step.** The pinned action's inline-comment tool only posts a new comment on a line
(`src/mcp/github-inline-comment-server.ts` calls `pulls.createReviewComment` with a path and line, and takes no
`in_reply_to`), so Claude can't reply in a conversation. Rather than give it a tool that can, the structured output also
carries `retier`: each entry names a conversation, its new tier, a one-line title and the reason. The step posts the
reply as the review App, `POST …/pulls/<n>/comments` with `in_reply_to` set to the conversation's first comment, and
writes the label line itself, so its form is always the one D1 parses. It applies the same checks against the snapshot
(on the pull request, unresolved, opened by the review), and skips a re-tier to the tier it already has, one with no
title or reason, and one for a conversation also named in `resolve`, which is only resolved. So the review re-tiers by
replying, as the spec says, through a step whose every write is fixed.

The snapshot is written twice: to `.review-threads.json` in the workspace, for Claude's Read, and to `RUNNER_TEMP`,
which the resolving step reads. Claude has no tool that writes files, and the copy outside the workspace is out of its
reach anyway.

*Fallback, if the probe (task 1) shows the pinned action doesn't support `--json-schema`:* Claude ends its summary
comment with one line, `Resolve: <id> <id>`. The step reads it from the review App's latest summary comment. The
checks against the snapshot are the same, so the trust doesn't change. Only where the list comes from does.

### D5. The guard allows `resolveReviewThread` for a nit only

`resolveReviewThread` joins `GH_MUTATIONS_ALLOWED` with a condition. The guard reads the mutation's `threadId`, which
must be a string literal in the query or one `-f`/`-F` field. It refuses anything else: a mutation naming two
conversations, a variable from a file, or stdin. Then it reads the conversation's first comment and its last 100,
in one query with a timeout:
`gh api graphql -f query='query{node(id:"…"){… on PullRequestReviewThread{first:comments(first:1){…} last:comments(last:100){nodes{author{login} body}}}}}'`.
It allows the mutation only if `troupe-run-review[bot]` wrote the first comment and D1 parses the review's latest
comment among the last 100 as a nit. The tier is the latest label, so the last 100 is the part that matters. If none
of them is the review's, the conversation counts as unlabelled and the resolve is refused.

GitHub's GraphQL API names the App as an author `troupe-run-review`, with `__typename` `Bot` (read from #193's
conversations, 2026-10-27), not `troupe-run-review[bot]` as REST does. A person could register that login, so both
the guard and the resolving step check the type as well as the login.

A failed read refuses the mutation. That's the guard's first online read in a hook. It's acceptable because the
command it judges is itself online. `unresolveReviewThread` stays refused, with no `gh` equivalent: reopening is the
owner's.

The rule is under `gh-allow-list`. Its refusal for a must-fix says the review resolves it on its next run once it's
addressed, and to raise a dispute with the owner. Its refusal for a decision or an unlabelled finding says to ask the
owner.

Checked on 2026-10-27, against gh 2.103.3 (the latest release, 2026-10-26), GitHub's REST docs and its GraphQL schema:
`gh pr` has no command for conversations (`gh pr review` only approves, comments or requests changes). gh's request
for one was closed as a duplicate of cli/cli#359, which is still open and "not in our roadmap", and a pull request
adding it (cli/cli#12482) was closed unreviewed. REST's review-comment endpoints list, create, edit, delete and reply,
but can't resolve. The schema has `resolveReviewThread` and `unresolveReviewThread`. So GraphQL is the only way, and
"one way per write" holds. The extension the gh maintainers point to isn't an option: the guard refuses extensions.

**The author's reply** before resolving a nit needs no new grant. gh has no command for replying in a conversation
either, but the guard already allows `POST repos/<owner>/<repo>/pulls/<n>/comments`, and REST's `in_reply_to` field
makes that a reply in the conversation: `gh api -X POST repos/<o>/<r>/pulls/<n>/comments -F in_reply_to=<comment id>
-f body=…`. That's the one way to reply. The `…/comments/<id>/replies` endpoint and `addPullRequestReviewThreadReply`
stay refused. A top-level `gh pr comment` doesn't count as a reply, because it isn't in the conversation.

*Alternative:* allow any resolve, and have the review reopen must-fix or decision conversations resolved by anyone
but itself. Rejected, because it would also reopen the owner's decisions: the owner and an agent are the same login.

### D6. The step reaches every change through the guide and `openspec/config.yaml`

The guide's step 4 ("Before the merge") gains the review step ahead of the archive. This repository's
`openspec/config.yaml` context gains one line under "Working", so `/opsx:propose` writes a task for it. Our test for
that is the next change proposed here.

troupe's and website's `config.yaml` are their own files, so they change by a pull request in each repository, under
issues this change opens. The issue's "Done when" ("each repository's changes include that step") is met only when
those pull requests merge, so #194 stays open until then.

### D7. A merge doesn't wait for the review

Nothing makes a merge wait for the review of the last push. Making it wait means either making the review a required
check, so a broken Claude token or a timeout would block every merge, or adding a check that waits on it. The owner
chose GitHub's native mechanism over a custom check (2026-10-27).

So a pull request merged while its review is still running merges past whatever that review would have found. The
workflow says to wait. Agents follow it, and the owner merges by hand. Revisit this only if a merge ever beats its
review.

### D8. Order of delivery

The workflow and guard changes merge first and are delivered by the apply. In the same apply, the ruleset turns on
conversation resolution in all three repositories. Before the plan is approved, list every open pull request's
unresolved conversations in the three repositories, so the owner knows what the switch will block.

Conversations from before this change have no label (D1). The review can't resolve them, and an agent can't either,
so they fall to the owner, or to a re-review that posts the finding again with a label.

## Probe results

- **Structured output (task 1.5, 2026-10-27).** `anthropics/claude-code-action` at the pinned SHA (`925afb5`, v1.0.262)
  declares the output `structured_output`: "JSON string containing all structured output fields when --json-schema is
  provided in claude_args" (`action.yml`, line 182). `base-action/src/run-claude-sdk.ts` sets it from the SDK's result
  message, and fails the step ("--json-schema was provided but Claude did not return structured_output") when there
  is none. So D4 takes its primary path, not the fallback. Two consequences for the workflow: the resolving step reads
  the output through an environment variable, never interpolated into its script (the docs' own example pastes it into
  a shell line, which a pull request's text could break out of); and a review that returns no structured output fails
  its step, so the resolving step runs only when the review succeeded, and resolves nothing otherwise.

- **What an open conversation blocks (tasks 1.2, 1.3, 2026-10-28)**, on `troupe-run/infra-probe-review-threads`, whose
  `protect main` ruleset had `required_review_thread_resolution` and a rebase merge queue (`rules/branches/main` listed
  both). The review App posted an inline comment on two pull requests, with a token minted as the workflow mints it
  (contents read, metadata read, pull requests write, the one repository).
  - The open conversation blocked the merge: `mergeStateStatus` BLOCKED, `mergeable` MERGEABLE.
  - `gh pr merge --rebase` didn't refuse ("The merge strategy for main is set by the merge queue"): it turned on
    auto-merge, with method SQUASH, and the pull request stayed out of the queue.
  - The owner's bypass, `gh pr merge --rebase --admin`, merged the other pull request past its open conversation.
  - Once the conversation was resolved, the pull request read CLEAN with auto-merge still on, but in three minutes it
    neither merged nor joined the queue. So whether auto-merge lands a pull request the moment its last conversation
    is resolved isn't settled. If it does, the owner's merge click stops being a look at the final state.
- **Who can resolve (task 1.4, 2026-10-28).** The review App's token **can't**: `resolveReviewThread` returned
  FORBIDDEN, "Resource not accessible by integration". A token holding **only `contents: write`** (the infrastructure
  App's, scoped to the probe) resolved the same conversation. So resolving needs contents write, which pull requests
  write doesn't give. The review App's token could still minimize its own comment (`minimizeComment`), and was refused
  a contents write (403), as designed. **This breaks D4 as written**: giving the review App contents write is what
  claude-pr-review design D1 rules out, so who resolves a must-fix goes back to the owner (#194).

## Risks / Trade-offs

- [The review disagrees with itself across runs, opening a finding it earlier let pass] → It's a new conversation, the
  author answers it as any other, and the owner sees it only if it's disputed.
- [Claude mislabels a real bug as a nit, and the author resolves it] → "Unsure means must-fix" (D1) narrows it. The
  author's reply is on record next to the line, and the next run sees the code: the prompt tells the review to post a
  fresh must-fix when it disagrees with a resolved nit. The look back (task 7) checks how good the labels are.
- [Every finding is now a click or a reply] → A nit needs only a reply and a resolve from the agent. The owner
  clicks only for decisions, disputes, and people's own comments.
- [An agent resolves a decision, or a disputed must-fix, without the guard seeing it: a session without hooks, an
  override, or a browser-automation tool clicking Resolve in GitHub's UI] → Accepted, as #47 accepts it for merges and
  rulesets: GitHub can't tell the owner's login from an agent's, so the guard is the fence, and it judges commands, not
  clicks. The owner's merge is the backstop, since the pull request shows each resolved conversation and who resolved
  it. Closing the gap needs something only the owner holds, such as a key, which is the custom check the owner turned
  down (2026-10-27).
- [The guard's online lookup slows or breaks the resolve command when offline] → Refusal is the safe outcome, and
  offline it couldn't send the mutation anyway.
- [Prompt injection in a pull request asks the review to resolve everything] → D4's checks against the snapshot cap
  it at the review's own must-fixes.
- [`required_review_thread_resolution` on a ruleset behaves differently from branch protection, or the merge queue
  ignores it] → The probe (task 1) checks merging, queueing and the owner's bypass before anything depends on it.

## Migration Plan

1. Probe, on `troupe-run/infra-probe-review-threads`.
2. Merge this change: the workflow, the guard and the docs. The apply delivers to troupe and website and turns the
   ruleset setting on everywhere, after the owner has seen the list of open conversations (D8).
3. troupe's and website's `config.yaml` pull requests.
4. Rollback: set `required_review_thread_resolution` to false in the module and apply. The workflow's labels and
   resolving still work without it, and nothing else depends on the setting.
