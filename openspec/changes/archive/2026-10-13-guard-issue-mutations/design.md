# Design

## Context

- **How a GraphQL write is classified** (`scripts/guard.py`, `_classify_api`):
  - `graphql_mutations` lists the top-level fields of every mutation in the query, aliases included.
  - Any owner-only name gives `owner-only`. If every name is in `GH_MUTATIONS_ALLOWED`, the command is allowed.
    Otherwise it is `unlisted`.
  - `gh_decision` then refuses an unlisted call with `_not_listed(f"gh api {method} {endpoint}")`, so the message
    reads `gh api POST graphql isn't on the guard's gh allow-list`. The mutation isn't named. `NOT_LISTED_FIX` is
    the same for every unlisted command: ask the owner or extend the list, and "a read with fields needs -X GET". That
    last part is about REST, not GraphQL.
- **The allowed `gh` commands:** `GH_WORKFLOW_WRITES` allows `gh issue edit`, `gh issue close/reopen/create/comment`,
  and `gh pr create/edit/ready/close/reopen/comment/checkout/merge`, with every flag. `gh pr review` is not listed.
  `gh issue delete` and `gh issue transfer` are owner-only.
- **gh 2.102.0** (`gh issue edit --help`, checked 2026-10-13) has `--type`, `--remove-type`, `--add-blocked-by`,
  `--remove-blocked-by`, `--add-blocking`, `--add-sub-issue`, `--remove-sub-issue`, `--parent` and `--remove-parent`.
  So the guard already allows setting an issue's type and its relationships through `gh`. Only the GraphQL form of
  the same act is refused.
- **GitHub's GraphQL schema** (introspected with a read-only query, 2026-10-13, 262 mutations) has every mutation
  this design names: `updateIssueIssueType`, `addBlockedBy`, `removeBlockedBy`, `addLabelsToLabelable`,
  `removeLabelsFromLabelable`, `addAssigneesToAssignable`, `removeAssigneesFromAssignable`, `closeIssue`,
  `reopenIssue`, `createIssue`, `closePullRequest`, `reopenPullRequest`, `markPullRequestReadyForReview`,
  `convertPullRequestToDraft`, `updatePullRequest`, `createPullRequest`, `deleteIssue` and `transferIssue`.
- **The guard is delivered to troupe.** A change to `scripts/guard.py` reaches it only through a plan the owner
  approves after the merge.

## Goals / Non-Goals

**Goals:**
- Each routine write has one allowed way to do it: the `gh` command.
- A refused mutation says which mutation it was, and points to the allowed `gh` command when there is one, so an
  agent can do the routine write itself without the owner.

**Non-Goals:**
- Allowing GraphQL generally, or any mutation that has a `gh` equivalent. A refused one gets a hint to the `gh`
  command instead.
- REST writes. `GH_API_WORKFLOW_WRITES` still allows a few `gh api` writes (issue comments, labels, sub-issues,
  editing an issue, pull request review comments and reviews). Some have no allowed `gh` command (`gh pr review` isn't
  listed, and inline review comments have none), so applying "one way" there is a separate question for the owner.
- Owner-only acts: merging past rules, rulesets, org administration, and defining issue types (the `issue-types`
  REST endpoint is already owner-only).
- Making `deleteIssue` and `transferIssue` owner-only rather than unlisted. Both are refused today either way, so
  only the message differs. Noted under Risks, not changed here.

## Decisions

### D1. One way to do each write: the `gh` command, so no GraphQL mutation is allowed

`GH_MUTATIONS_ALLOWED` is emptied (owner, 2026-10-13). Every mutation it listed, and #30's three, has a `gh` command the
guard allows:

| Mutation | `gh` command |
|---|---|
| `updateIssue` | `gh issue edit <n>` (and `gh issue close` / `reopen` for its state) |
| `updateIssueIssueType` | `gh issue edit <n> --type <name>` |
| `addBlockedBy` / `removeBlockedBy` | `gh issue edit <n> --add-blocked-by <m>` / `--remove-blocked-by <m>` |
| `addSubIssue` / `removeSubIssue` | `gh issue edit <n> --add-sub-issue <m>` / `--remove-sub-issue <m>` |
| `addComment` | `gh issue comment <n>` or `gh pr comment <n>` |
| `addProjectV2ItemById` | `gh project item-add <number> --owner <org> --url <issue-url>` |
| `updateProjectV2ItemFieldValue` | `gh project item-edit --id <item> --field-id <field> --project-id <project>` |

A second route through GraphQL adds a way to review and nothing an agent needs. With no allowed mutations, a GraphQL
document with a mutation is refused: owner-only first, as today, otherwise `gh-allow-list` with the hint (D2, D3). A
GraphQL query with no mutation is still a read and still allowed.

Nothing in troupe, infrastructure or website calls these mutations (searched 2026-10-13). The guard's survey of earlier
sessions (refuse-admin-merge design D4) has one `updateIssue` call. That call is now refused with `gh issue edit <n>`
as its fix, and its survey test case changes to expect `gh-allow-list`.

The table `GH_MUTATIONS_ALLOWED` is kept, empty, rather than deleted. It is the one place a mutation would be added if
evidence ever shows a write `gh` can't do, and the classification code stays the same shape.

*Alternatives:* allow #30's three by name, as the issue first proposed, or keep the six already listed. Both rejected
by the owner: one way to do each thing.

### D2. A table of `gh` equivalents for unlisted mutations, kept next to the allow-list

A new `GH_MUTATION_EQUIVALENTS` maps an unlisted mutation to the `gh` command that does the same, written as the
agent would type it, with placeholders (`gh issue edit <n> --add-label <name>`). It holds D1's table, mutations whose equivalent the guard allows: labels, assignees, closing and reopening issues and pull requests, creating issues and pull requests, ready and draft, and editing a pull request.

Two tests keep it honest, so a hint can't send an agent to another refusal:
- every command in the table is allowed by `gh_decision` as written (placeholders filled with sample values);
- no mutation in the table is owner-only, and none is in `GH_MUTATIONS_ALLOWED`, so the table holds only
  mutations that are refused for being unlisted.

A mutation with no allowed equivalent (`deleteIssue`, whose `gh issue delete` is owner-only, or `addPullRequestReview`,
whose `gh pr review` is unlisted) has no entry, and its refusal names no command.

*Alternative:* derive the hint from gh's source at run time. Rejected because the guard is standard library only and
works offline. The names were checked against GitHub's schema once, here (Context), and the table records the result.

### D3. The refusal names the mutations, and its fix leads with the `gh` command

For a GraphQL write refused as unlisted:
- **Problem:** `GraphQL mutation updateIssueIssueType isn't on the guard's gh allow-list.` With several unlisted
  mutations, it names each one, in query order and without repeats.
- **Fix:** each unlisted mutation that has an equivalent gets one clause, such as `For updateIssueIssueType, run gh
  issue edit <n> --type <name>, which the guard allows.` The usual fix follows: ask the owner, or add it to the
  list in troupe-run/infrastructure (scripts/guard.py). The "-X GET" note is left out, because it is about REST.

REST refusals and the other `gh-allow-list` messages are unchanged. The rule id stays `gh-allow-list`, so overrides
and the rules doc are unaffected.

### D4. Docs

The `gh-allow-list` row in `docs/development-workflow.md` says that no GraphQL mutation is allowed, and that a refused
mutation is named, with the `gh` command when there is one.

## Risks / Trade-offs

- **The table can go stale as gh and GitHub change.** A renamed mutation would never match, so its hint would never
  show. That's a missing hint, not a wrong allowance: the tests stop the table from pointing to a refused command or
  from listing an allowed mutation. Each entry was checked against the live schema on 2026-10-13.
- **`deleteIssue` and `transferIssue` are refused as `gh-allow-list`, not `owner-only`,** although their `gh` forms
  are owner-only. An override of `gh-allow-list` could therefore let one through where `gh issue delete` would need
  an `owner-only` override. That isn't new and isn't widened here. It's worth its own issue.
- **Delivery:** troupe gets the new guard only after the owner approves the apply, so until then agents in troupe
  still see the old refusal.
