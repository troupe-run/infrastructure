# Proposal

## Why

Claude's review is told "Never resolve a decision or a nit", and its `resolve` job refuses anything but a must-fix. So
a nit stays open after a push fixes it, holding the merge until the author resolves it by hand, even when the review's
own summary says it's fixed (troupe-run/website#87: the nit `/\host` passes as a site path, fixed by b3fd1fa and
8373c61, still open). The review already reads every open conversation against the diff on each run, so it can see
when a nit no longer applies (#246, raised by the owner on 2026-11-01).

## What Changes

- The review's prompt (`.github/workflows/claude-review.yml`) lets Claude name a nit it opened in `resolve` when the
  diff shows the problem is gone. That's the review's call, not the author's duty, and a reply alone never resolves a
  nit: only a fix in the diff does. It still never names a decision, or anyone else's conversation.
- The `resolve` job's step accepts a nit as well as a must-fix. It still refuses a decision, an unlabelled
  conversation, a person's conversation, and one that's already resolved or not on the pull request.
- Unchanged: the author may still resolve a nit, with or without a fix (the guard's "An agent resolves only a nit"
  rule stays as it is); a reply to a nit still starts no review; a nit no push addresses stays open for the author.
- The workflow's comments, `docs/development-workflow.md` ("Claude's review"), this repository's `CLAUDE.md` and
  `openspec/config.yaml`, the org's contributing guide (`org-profile/CONTRIBUTING.md`), and the session-start summary
  the guard delivers to every repository (`WORKFLOW_SUMMARY` in `scripts/guard.py`, "resolve only nits") say it: the
  author may resolve a nit, and the review may resolve one that a push has fixed.
- troupe's and website's own `CLAUDE.md` and `openspec/config.yaml` carry the same wording. They change through
  their own pull requests, so this change raises an issue in each (on the roadmap board) rather than editing them.
- The new behaviour is checked on website#87, whose nit thread was left open as the live test: the first review of
  that pull request after the delivery resolves it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pr-review`: the review resolves its own nits once a push has fixed them, as well as its must-fixes; the nit tier
  says the author or the review resolves it; the resolving step's widening check allows nits and still refuses
  decisions.
- `development-workflow`: a new requirement that the contributing guide and each repository's OpenSpec context say
  the review resolves a nit a push has fixed, so the session may leave it for the review. "Review findings are acted
  on before a change is archived" is unchanged: adding to it would take it past 500 characters.

## Impact

- `.github/workflows/claude-review.yml`: the prompt, the header comment, and the `resolve` step's tier check. The file
  is a guard file, so it reaches troupe and website by delivery, in the apply the owner approves.
- `scripts/guard.py`: `WORKFLOW_SUMMARY` only, also delivered to troupe and website. The guard's rule on which
  conversations an agent may resolve doesn't change.
- `scripts/tests/test_claude_review_workflow.py`: the pinned hash of the resolve step, the test of which conversations
  are resolved, and a named case for a step widened to decisions.
- `org-profile/CONTRIBUTING.md` reaches troupe-run/.github through the same apply.
- `tofu/`: no source change; the plan shows the deliveries and the guide's update.
