## Why

Routine issue housekeeping still needs the owner (#30, from troupe-run/troupe#74 on 2026-10-13). An agent set an
issue's type and added a "blocked by" link through `gh api graphql` with `updateIssueIssueType` and `addBlockedBy`.
The guard refused both as `gh-allow-list`, although it already allows the same writes through `gh issue edit --type`
and `gh issue edit --add-blocked-by`. The refusal's fix said to ask the owner or extend the list. It didn't name the
`gh` command that would have worked, so the owner ran them by hand.

## What Changes

- **One way to do each write: the `gh` command.** No GraphQL mutation is allowed any more (owner, 2026-10-13).
  #30's three (`updateIssueIssueType`, `addBlockedBy`, `removeBlockedBy`) stay refused, and the six listed today
  (`updateIssue`, `addSubIssue`, `removeSubIssue`, `addComment`, `addProjectV2ItemById`,
  `updateProjectV2ItemFieldValue`) are removed. Each has a `gh issue`, `gh pr` or `gh project` command the guard
  allows. **BREAKING** for an agent that used one of the six; nothing in the org's repositories does. A GraphQL query
  with no mutation is still allowed.
- **A refusal of an unlisted mutation names it**, rather than only `gh api POST graphql`.
- **When the refused mutation has an allowed `gh` equivalent, the fix names that command.** For example,
  `updateIssueIssueType` → `gh issue edit <n> --type <name>`, `addBlockedBy` → `gh issue edit <n> --add-blocked-by
  <m>`, `addLabelsToLabelable` → `gh issue edit <n> --add-label <name>`, and `markPullRequestReadyForReview` →
  `gh pr ready <n>`. A mutation whose `gh` equivalent is owner-only (`deleteIssue`, `transferIssue`) gets no hint.
  Every hinted command is one the guard allows, and a test checks that.
- **`docs/development-workflow.md`** says the same in the `gh-allow-list` row.

Not in this change: #30's question about Claude Code permission rules. The owner prefers that the guard's hook
allow its own allow-listed `gh` commands, with safeguards, over shipping rules in the delivered
`.claude/settings.json`. That changes what the guard does, so it is #31.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: the requirement "Agents' gh commands are allow-listed" says an everyday write is allowed
  through its `gh` command only, never as a GraphQL mutation; a refused mutation is named, and the fix names the
  allowed `gh` command when there is one.

## Impact

- `scripts/guard.py`: `GH_MUTATIONS_ALLOWED` emptied, a new table of `gh` equivalents for unlisted mutations, and
  the `gh-allow-list` refusal for GraphQL. The guard is a delivered file, so after the merge the owner's approved apply
  delivers it to troupe.
- `scripts/tests/test_guard_gh.py`: tests for the refused mutations, the named refusal and the hints.
- `docs/development-workflow.md`: the `gh-allow-list` row.
- Out of scope: owner-only acts (merging past rules, rulesets, org administration, defining issue types), and
  GraphQL generally.
