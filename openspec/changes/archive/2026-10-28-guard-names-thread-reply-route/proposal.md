# Proposal

Issue: #210.

## Why

On troupe-run/troupe#186 a session replied to a review finding with GraphQL's `addPullRequestReviewThreadReply`. The
guard refused it, as it should, but the fix said only "Ask the owner, or add it to the list". It didn't name the one
allowed way to reply, `gh api -X POST repos/<owner>/<repo>/pulls/<n>/comments -F in_reply_to=<comment id> -f
body=...`. So the session asked the owner to allow the mutation, which would give replying a second way and break "each
everyday write has one way to do it". The `.../comments/<id>/replies` endpoint has the same gap.

A second trap: a `resolveReviewThread` whose thread id is a shell variable (`threadId: "$TID"`) is refused with "Check
gh's login and network", because the guard reads the id from the command's text and looks up `$TID` itself. The fix
sends the session after its login, not the variable.

## What Changes

1. **A refused reply names the allowed reply.** Refusing `addPullRequestReviewThreadReply` names the `gh api ...
   pulls/<n>/comments -F in_reply_to=<comment id>` command in its fix. Refusing a `POST` to
   `repos/<owner>/<repo>/pulls/<n>/comments/<id>/replies` names the same command, filled in from that endpoint
   (design D1, D2).
2. **A fix with a way doesn't also invite adding to the list.** When every refused mutation or endpoint in a command
   has an allowed way, the fix names those ways only, and drops "Ask the owner, or add it to the list". It stays for
   anything that has no allowed way (design D3). This applies to every mutation already in `GH_MUTATION_EQUIVALENTS`,
   not only the reply.
3. **A thread id the shell fills in is refused for what it is.** A `resolveReviewThread` whose id, in the query or in a
   `-f`/`-F` field, holds a shell expansion (`$NAME`, `${...}`, `$(...)` or a backtick) is refused before any lookup,
   with a fix that says to write the id out (design D4).

`docs/development-workflow.md`: "Replying in a conversation" says the refusal names the allowed command; "Resolving a
nit" says the id is written out, not passed through a shell variable.

Out of scope: allowing any further way to reply or resolve, and reading shell variables' values.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: "Each everyday gh write has one way to do it" now covers a write whose one way is an allowed
  `gh api` call, refused REST endpoints as well as mutations, and a fix that names a way without inviting an addition
  to the list. "An agent resolves only a nit" gains a scenario for a thread id passed through a shell variable.

## Impact

- `scripts/guard.py`: `GH_MUTATION_EQUIVALENTS`, a new table of refused API writes with an allowed way,
  `_not_listed_mutations`, `gh_decision`'s unlisted-endpoint refusal and `review_resolve_decision`. Delivered, so
  troupe and website receive it after the owner approves the delivery plan (`guard_targets` in
  `tofu/guard_delivery.tf`). The plan changes only `scripts/guard.py` in each of the two.
- `scripts/tests/test_guard_review_threads.py` and `scripts/tests/test_guard_gh.py`: tests for each refusal's fix.
- `docs/development-workflow.md`: the two sections above.
- No command that's allowed today is refused, and no refused command becomes allowed: only refusals' messages change.
