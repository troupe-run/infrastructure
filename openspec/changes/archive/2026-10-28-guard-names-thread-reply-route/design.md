# Design

## Context

See proposal.md for why. In `scripts/guard.py` today:

- `GH_MUTATION_EQUIVALENTS` maps a refused GraphQL mutation to the `gh` commands that do the same write, and
  `_not_listed_mutations` puts "For X, run Y, which the guard allows." in front of a fixed tail, "Ask the owner, or add
  it to the list in troupe-run/infrastructure (scripts/guard.py)." The tail is there even when every mutation has a
  way. Its comment says it holds only `gh` commands, so the reply, whose one way is a `gh api` call
  (`GH_API_WORKFLOW_WRITES`' `pulls/<n>/comments` `POST`), has no entry.
- A `gh api` write to an endpoint `GH_API_WORKFLOW_WRITES` doesn't match is refused by `_not_listed` with
  `NOT_LISTED_FIX`, which never names a way.
- `_resolved_thread_id` takes the id from `threadId: "..."` in the query, or from the `-f`/`-F` field a `threadId:
  $var` names. By then the shell's quoting is gone but its expansions aren't, so `"$TID"` reaches `read_review_thread`
  as the text `$TID`, GitHub can't resolve it, and the refusal blames the read.
- `SHELL_EXPANSION` (`$NAME`, `${`, `$(`, backtick) already exists for the pull request body check.

## Goals / Non-Goals

**Goals:** every refusal of a reply names the one allowed reply; a thread id the shell fills in gets a fix about the
id; no command's verdict changes.

**Non-Goals:** expanding shell variables, or guessing their values; a general mapping from every refused REST endpoint
to an allowed one. Only the replies endpoint is mapped, since it's the one with a known one-way twin.

## Decisions

### D1. The reply goes in `GH_MUTATION_EQUIVALENTS`

Add `"addPullRequestReviewThreadReply": ("gh api -X POST repos/<owner>/<repo>/pulls/<n>/comments -F
in_reply_to=<comment id> -f body=<text>",)` and widen the table's comment from "the gh command" to "the allowed
command, a `gh` command or, for a write `gh` has no command for, its one `gh api` call". The rule for an entry stays:
only a command the guard allows. A test holds each entry to that by running it through `gh_decision` with its
placeholders filled in, so an entry can't name a refused command.

*Alternative:* a separate table for `gh api` ways. Rejected: the refusal reads the same either way, and one table keeps
the decision in one place.

The mutation's input carries a thread id (`PRRT_...`), not the comment id `in_reply_to` needs, so the fix keeps
placeholders rather than trying to fill them in.

### D2. Refused API writes with a way: `GH_API_EQUIVALENTS`

A new tuple beside `GH_API_WORKFLOW_WRITES` of (endpoint pattern, methods, template), first entry the replies endpoint:
`repos/(owner)/(repo)/pulls/(n)/comments/(id)/replies`, `POST`, giving `gh api -X POST
repos/{owner}/{repo}/pulls/{n}/comments -F in_reply_to={id} -f body=<text>`. The template is filled from the
endpoint's groups, since here everything the allowed call needs is in the refused one. `gh_decision`'s unlisted-endpoint
branch checks it before falling back to `_not_listed`; the refusal's problem is unchanged ("gh api POST ... isn't on
the guard's gh allow-list"), and the fix becomes "Run <command>, which the guard allows." The same entries-are-allowed
test covers it.

*Alternative:* placeholders only, like D1. Rejected: the endpoint holds every value, so a filled-in command is one the
session can run as written, and is harder to misread.

### D3. A fix with a way doesn't invite an addition to the list

The trap in #210 was the session reading "add it to the list" as the remedy. When every refused mutation in a command
has an entry, `_not_listed_mutations` ends with the hints alone. When some don't, it keeps the hints and ends with
"For <names without one>, ask the owner, or add it to the list in troupe-run/infrastructure (scripts/guard.py)." D2's
fix has no tail either. This changes the message for every existing entry, not only the reply; the existing
`addLabelsToLabelable` test gains an assertion that the fix doesn't say "add it to the list".

*Alternative:* keep the tail and only add the reply's hint, as the issue's "done when" asks at minimum. Rejected: the
tail is what sent the session to the owner, and it would keep doing so for every other mutation with a way. Taking it
off changes no verdict, and adding to the list stays the owner's call through an issue, as before. This is the one
choice here past the issue's letter; the owner can reverse it by restoring the tail.

### D4. A shell expansion in the thread id is refused before the lookup

In `review_resolve_decision`, after `_resolved_thread_id` returns an id, refuse when `SHELL_EXPANSION` finds anything
in it: problem "the conversation's id (<id>) is filled in by the shell, so the guard can't read it before it runs";
fix "Write the conversation's id out in the command: threadId: \"PRRT_...\" or -f <variable>=PRRT_...". No call to
`gh` is made. This covers `threadId: "$TID"` in a double-quoted query, `-f id=$TID` and `-F id="$(cat f)"`.

Because quoting is gone by then, a single-quoted literal `'$TID'` gets the same refusal. That's right: no GitHub node
id contains `$` or a backtick, so such an id can't name a conversation either way, and the fix still applies.

*Alternative:* match the id against GitHub's node id shape and refuse anything else. Rejected for now: the shape isn't
documented, and an id that's merely wrong already gets "isn't a review conversation" from GitHub, which is accurate.

## Risks / Trade-offs

- [An entry names a command the guard later refuses, so a refusal points at another refusal] → the test in D1 runs every
  entry of both tables through `gh_decision`, so tightening the allow-list fails the suite until the entry goes.
- [D3 changes refusal text other tools or docs quote] → the only readers are sessions and
  `docs/development-workflow.md`, which the tasks update; no test elsewhere matches the tail (checked by grep in tasks).
- [Delivery reaches open pull requests' guard runs only on rebase] → messages only; no verdict changes, so nothing goes
  red.

## Migration Plan

Delivered as usual: after merge, the owner approves the plan that writes `scripts/guard.py` into troupe and website.
Rollback is a revert and another delivery.
