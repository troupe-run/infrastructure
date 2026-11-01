# Design

## Context

See proposal.md for why. What shapes the approach:

- `claude-review.yml`'s `review` job runs Claude, which reads `.review-threads.json` (every review conversation, its
  state and its last 100 comments) and finishes with structured output `{resolve, retier}`. Its prompt says: "Never
  resolve a decision or a nit, nor anyone else's conversation."
- The `resolve` job's step "Resolve and re-tier what Claude named" checks each named conversation against the snapshot
  the job reads itself, never against what Claude says: it must exist, be open, have been opened by
  `troupe-run-review` (a Bot), and its tier, the review's latest label in it, must be must-fix
  (`if current != "must-fix":`). The step's script is pinned by hash in
  `scripts/tests/test_claude_review_workflow.py`, and `test_only_the_review_s_open_must_fixes_are_resolved` fixes which
  of ten conversations are resolved.
- The `gate` job starts a review for a pull request event, or for a person's reply in an open **must-fix** only. A
  reply to a nit starts no run.
- The guard's rule "An agent resolves only a nit" (`GH_MUTATIONS_CONDITIONAL`) governs what an agent may resolve, not
  what the review may. It doesn't change.

## Goals / Non-Goals

**Goals:**
- A nit fixed by a push is resolved by the review of that push, or a later one, without anyone resolving it by hand.
- The resolving step still refuses, on its own snapshot, everything that isn't the review's own must-fix or nit.

**Non-Goals:**
- Starting a review on a reply to a nit. A nit is resolved by the review only on a fix, and a fix is a push, which
  already starts a review.
- Changing who else may resolve a nit, or what the guard allows an agent.
- Resolving a nit on the author's say-so ("fixed in abc123" with no push since, or "not worth it"). The author
  resolves those, as now.

## Decisions

### D1. Claude resolves a nit only when the diff shows the problem gone

The prompt's list for each open conversation the review opened becomes:

- a must-fix whose problem is gone, or whose author's reply settles it: name it in `resolve`;
- a nit whose problem is gone from the diff: name it in `resolve`. A reply alone doesn't settle a nit for you: if
  nothing in the diff fixes it, it stays open for the author;
- a wrong tier: `retier`, as now;
- anything else stays open. Never resolve a decision, nor anyone else's conversation.

The nit tier's definition changes from "The author resolves these." to "The author resolves these, or you do once a
push has fixed one." The summary already reports each earlier finding as fixed, still open and so on; a resolved nit
is reported as fixed.

**Why the diff and not a reply:** a nit's reply is the author saying what it did, and the author can resolve it then.
A must-fix's reply is resolved by the review because the author may not resolve it; a nit has no such gap. Keeping
the review to the diff also means it acts only on what it can see, and the gate needn't change (a reply to a nit
still costs no run).

**Alternative: leave the prompt saying "never a nit", and resolve every nit whose thread GitHub marks outdated.**
`isOutdated` only says the lines moved, not that the problem is gone: a reformat would close an unfixed nit, and a
fix elsewhere in the file would leave it open. Rejected.

### D2. The step accepts must-fix or nit, and nothing else

`if current != "must-fix":` becomes a check that the tier is one of must-fix and nit, and the warning for anything
else says only a must-fix or a nit is the review's to resolve. The other checks (exists, open, opened by the review)
are unchanged, and the order still puts a re-tier and a resolve of the same conversation down to "only resolved".

Since the tier is read from the snapshot, a nit the review re-tiered to must-fix, or a must-fix re-tiered to nit, is
resolvable either way; a conversation re-tiered to decision isn't. A label in a person's reply still counts for
nothing.

**Why a tuple of allowed tiers, not "not a decision":** an unlabelled conversation (its label doesn't parse) must
still be refused, and a new tier added later shouldn't become resolvable by default.

### D3. Tests

- The step's pinned hash is updated, as any change to its script requires.
- `test_only_the_review_s_open_must_fixes_are_resolved` becomes `test_only_the_review_s_open_must_fixes_and_nits_are_resolved`:
  of the same ten conversations, `PRRT_mustfix`, `PRRT_upgraded`, `PRRT_downgraded`, `PRRT_nit` and
  `PRRT_selflabel` (a nit whose only must-fix label is a person's) are resolved, and a warning names each of the other
  five.
- `test_each_way_the_workflow_can_go_wrong_is_named` keeps its case for the tier check replaced with `if False:`
  (rewritten for the new line), and gains one where `"decision"` is added to the allowed tiers, so widening to
  decisions is named as a changed script.
- Nothing pins the prompt's resolve list today. A new test checks the prompt no longer says "Never resolve a
  decision or a nit", and does tell Claude to name a nit only when the diff shows it fixed and never a decision.

### D4. Wording in each place, and troupe's and website's own files

"Resolve only nits" stays true of the author everywhere it's written, so each place keeps it and adds that the review
resolves a nit a push has fixed:

- `docs/development-workflow.md`, "Claude's review": the nit row's "Who resolves it" becomes "the author, after
  replying with what it did …; or the review, on the run for the push that fixed it". The paragraph on replies notes
  that a nit fixed by a push needs no reply or resolve.
- `CLAUDE.md` step 5 and `openspec/config.yaml`'s context, in this repository.
- `org-profile/CONTRIBUTING.md`, step 4: "the author resolves it" becomes "the author resolves it, or the review does
  once a push has fixed it".
- `WORKFLOW_SUMMARY` in `scripts/guard.py`: "resolve only nits" becomes "resolve only nits; the review resolves the
  must-fixes and the nits a push fixed". No test pins it today; the session-start hook's output is checked by
  running it.
- The workflow's header comment says the `resolve` job resolves the review's own must-fixes and the nits a push fixed.

troupe's and website's `CLAUDE.md` and `openspec/config.yaml` also say "resolve only nits", and the
development-workflow requirement now asks their contexts to say the review resolves fixed nits. They're product repos,
so they change through their own pull requests: this change raises one issue in each, added to the roadmap board, and
links them from #246. Until those merge, their wording is incomplete but not wrong: the author resolving a fixed nit
is still allowed.

## Risks / Trade-offs

- [Claude resolves a nit that isn't really fixed] → The worst outcome of a nit left as it is is a reader briefly
  misled, by the tier's own definition. The summary says it was fixed, and the author or owner can reopen it. A nit
  the author resolved that matters is posted again as a must-fix, as now.
- [The author and the review both resolve the same nit] → The step warns "already resolved" when the snapshot shows
  it; if the author resolves it between the snapshot and the mutation, resolving a resolved conversation is harmless.
- [A nit that matters is quietly closed by the review instead of being looked at by the author] → Only when the diff
  shows the problem gone, which is the same evidence the author would act on.
- [The live test depends on website#87 still being open after the delivery] → If it has merged or the thread was
  resolved by then, open a pull request in website (or troupe) whose nit is fixed by a later push, after the delivery.

## Migration Plan

1. Merge, then the owner approves the apply, which delivers `claude-review.yml` and `scripts/guard.py` to troupe and
   website and updates `CONTRIBUTING.md` in troupe-run/.github.
2. A new pull request event on website#87 runs the delivered workflow (re-running an old run reuses the old file).
   The session that owns #87 pushes a rebase onto website's main; ask in that session or the owner rather than
   pushing to its branch from here. Its review reads the open nit, sees `/\host` refused in the diff, and its
   `resolve` job logs `<id>: resolved.` Record that run on #246.
3. Rollback: revert the commit; the next apply delivers the old file, and the review again leaves nits to the
   author.
