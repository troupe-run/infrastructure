# Proposal: Require troupe's one check result instead of its 12 check legs

## Why

troupe's `ci-check-scope` change (troupe-run/troupe#101, pull request #117) makes troupe's CI run only what each push's
changed paths need. A push that only archives a change or ticks tasks, after a push whose `check` passed, skips all 12
legs, and GitHub reports a skipped matrix job under its unexpanded name. So the 12 contexts
`check (<os>, Python <version>)` that troupe's ruleset requires never report for that head, and the pull request can't
merge. troupe's new `check` job reports for the legs instead, and it's the check the ruleset has to require (#104).

## What Changes

- `tofu/required-checks.json` requires `check` from GitHub Actions for troupe, in place of the 12 legs. troupe's
  `guard (workflow rules)` and `DCO` stay as they are.
- A test pins troupe's list: it requires `check` and no `check (...)` leg.
- The comments and docs that name troupe's legs as its required checks say `check` instead: `tofu/repositories.tf`
  and the README's rulesets section.
- **Order: this change merges and is applied first, then troupe's #117 merges.** #117's own runs already report
  `check` (and all 12 legs), so the new ruleset doesn't block it. The other order would block #117 itself: its archive
  push skips the legs, and the old ruleset would wait for them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `rulesets`: troupe requires its one CI `check` result rather than each CI check job, and a troupe pull request whose
  legs were all skipped can merge.

## Impact

- `tofu/required-checks.json`, `tofu/repositories.tf` (a comment), `README.md`,
  `scripts/tests/test_required_checks.py`.
- troupe's live ruleset "protect main": its required status checks change from 14 to 3, shown in the pull request's
  plan and changed only by the owner-approved apply.
- Between the apply and #117's merge, a troupe pull request based on the old `ci.yml` can't merge, because nothing on
  it reports `check`. The only other open one is release-please's #89, which is regenerated from `main` after #117
  merges.
