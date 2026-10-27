# Proposal

## Why

Claude's review (#154, #161) posts its findings on every pull request, but nothing in the workflow reads them: the
guide goes from "checks pass" to archiving, and #187 merged with a finding still on it (#194). A review nobody acts on
is noise. The owner wants each finding acted on before the merge, by its kind, without deciding every one
themselves: they want to be involved only when a finding is unclear or is a real choice (owner, 2026-10-27).

## What Changes

- **Every finding is an inline conversation with a tier.** The review labels each finding **must-fix**, **nit** or
  **decision**, named for who resolves it, and posts it on the lines it's about, as it does now, so it keeps its
  context. A must-fix is anything someone other than the author should check before it merges; a nit is anything
  whose worst outcome is a reader briefly misled or untidy code; a decision is a choice the design doesn't settle and
  that's hard to reverse or reaches beyond the pull request. Unsure between must-fix and nit means must-fix (owner,
  2026-10-27). The summary comment lists them, decisions and must-fixes first. A finding that isn't about specific
  lines goes on the closest line it concerns, so it's still a conversation.
- **Every conversation must be resolved before a merge.** The `main` ruleset of troupe, infrastructure and website
  turns on GitHub's `required_review_thread_resolution`, which also stops a pull request joining the merge queue.
- **Who resolves a conversation is its tier** (owner, 2026-10-27):
  - **nit:** the session that owns the change, once it has replied saying what it did (fixed it, raised a follow-up
    issue, or not useful and why).
  - **must-fix:** the review, on its next run, when the problem is gone from the diff or the author's reply convinces
    it. The session can't resolve these. One still disputed after the re-review goes to the owner.
  - **decision:** nobody but the owner. The session raises it with the owner.
- **The tier follows the conversation.** Only the review changes it, by replying with a new label and its reason: a
  must-fix can become a decision or a nit, and a nit a must-fix. The author argues for a change by replying; a label in
  the author's reply counts for nothing, since an agent's reply and the owner's come from the same login.
- **The review resolves its own conversations** through a fixed workflow step, not a new tool: a step before Claude
  writes the pull request's review conversations to a file Claude reads, and a step after it resolves exactly the ones
  Claude names, and only the review App's own must-fixes, with the App's token. Claude's tool list doesn't grow.
- **The guard lets an agent resolve a nit, and nothing else.** `resolveReviewThread` becomes the one allowed GraphQL
  mutation (gh has no command for it), granted only when the conversation was opened by `troupe-run-review[bot]` and
  its tier, the review's latest label in it, is nit. Any other conversation stays the owner's or the review's. An agent
  that gets past the guard (no hooks, an override, a click in GitHub's UI) could still resolve one: that's the gap #47
  accepts everywhere, and the owner's merge is the backstop.
- **The workflow says what to do before archiving.** The org's contributing guide, `docs/development-workflow.md`,
  and each governed repository's `openspec/config.yaml` context (so every change's tasks carry it) gain the step: wait
  for the review of the last push, act on each finding by its tier, and raise decisions and disputes with the owner.
- **A probe first**, on a throwaway `troupe-run/infra-probe-*` repository: that an unresolved conversation opened by
  an App blocks a rebase merge and the merge queue, that the owner's bypass still merges past it, and that a token for
  an App holding `pull_requests: write` can resolve and only resolve conversations.
- **A look back** at the 16 pull requests merged since the review was delivered (#157 onwards in infrastructure,
  troupe#183 and website#70), so no must-fix was missed. Anything that was gets an issue.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pr-review`: findings are must-fix, nit or decision, and are all inline conversations; a conversation's tier is
  the review's latest label in it; the review reads its earlier conversations on each run and resolves its own
  must-fixes once addressed; it is no longer purely advisory, because its open conversations block a merge.
- `rulesets`: a pull request into `main` merges only once every review conversation is resolved.
- `development-workflow`: the guard allows an agent to resolve a nit, and no other conversation; findings are acted
  on before a change is archived.

## Impact

- `.github/workflows/claude-review.yml` (prompt, two new steps) and `scripts/tests/test_claude_review_workflow.py`;
  delivered to troupe and website with the guard's files.
- `scripts/guard.py` (`resolveReviewThread`, with a lookup of the conversation before it's allowed) and its tests;
  delivered.
- `tofu/modules/repository/main.tf` (`required_review_thread_resolution`), applied to all three repositories after
  the review that resolves its own conversations is delivered, so no pull request is stuck on conversations nothing
  can resolve.
- `org-profile/CONTRIBUTING.md` (published to `troupe-run/.github`), `docs/development-workflow.md`, `CLAUDE.md`,
  this repository's `openspec/config.yaml`; troupe's and website's `openspec/config.yaml` by pull request in each,
  under issues this change opens.
- Open pull requests when the ruleset applies: any review conversation already on them blocks their merge until it's
  resolved. Earlier conversations carry no tier, so the guard won't let an agent resolve them; the owner resolves them,
  or the review posts the finding again with a tier.
- A failed review opens no conversation, so it blocks nothing. Equally, nothing makes a merge wait for the review of
  the last push: the workflow says to wait, but a pull request merged before the review posts merges past whatever
  it would have found (design D7).
