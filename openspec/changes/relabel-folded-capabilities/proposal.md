# Proposal

Issue: #151, its second and last change. The first was #158 (PR #160), which made the drift check read each troupe
spec's `Capability:` line and created `cap:development`.

## Why

troupe-run/troupe#169 folded 12 spec-level labels into the capability labels their specs now name, and removed
`cap:lifecycle` (owner, 2026-10-26). The specs on troupe's `main` already name the new labels, and #160 created the
one that was missing. The 12 folded labels are still declared and still on troupe's issues, so an issue about
`run-workspaces` says `cap:run-workspaces` and not `cap:stages` or `cap:vcs`, and the label list holds 49 entries
where #169 decided on 36.

They can't simply be deleted. The `labels` spec says a capability label that any issue or pull request carries is
never removed, because deleting a declared label takes it off every issue. #169 decided the order: every issue that
carries a folded label first gets **every** label its spec now names, and only then is the folded label removed.

## What Changes

- **troupe's issues are relabelled, before the pull request.** Each troupe issue and pull request that carries one of
  the 12 folded labels gets every label that the folded label's spec names in its `Capability:` line on troupe's
  `main`, and then loses the folded label. Read on 2026-10-26: 59 label uses on 43 issues (14 open, 29 closed) and no
  pull requests. 36 of the issues need 43 labels added; the other 7 already carry every label their specs name
  (design D1, D2). It's done with `gh issue edit`, all additions first and all removals second, and verified against
  GitHub (design D3).
- **The 12 folded labels and `cap:lifecycle` are removed from `tofu/labels/troupe.json`** (49 → 36). By then each of
  the 13 is on nothing, so the plan deletes 13 labels and no issue loses a label (design D4).
- **The fold is written into the `labels` spec** as a scenario of "A capability label in use is never removed or
  renamed", so a future fold follows the same order.
- **No oob record is keyed by a removed label.** `oob/troupe-spec-purposes.json` has been keyed by spec since #160,
  and the specs it records (`artifact-store`, `config-files` and the rest) all still exist; no other file in `oob/`
  names a `cap:` label. Nothing there changes, and the apply checks it again (design D5).

The folded labels are:
`cap:claude-code-runner`, `cap:scripted-runner`, `cap:runner-protocol`, `cap:run-workspaces`, `cap:config-files`,
`cap:artifact-store`, `cap:client-protocol`, `cap:flake-hunt`, `cap:python-support`, `cap:quality-check`,
`cap:releases` and `cap:docs-publishing`.

Out of scope:
- The roadmap board's `Capability` options. The board already has no option for a folded label. Removing its
  `lifecycle` option, and the check that keeps the options in step with the labels, are #152's (merged after this).
- Trimming a label added here that turns out not to fit an issue. #169 chose every label over a guess; trimming is a
  later, ordinary edit.
- Any change to troupe-run/troupe's files, or to `scripts/oob.py`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `labels`: "A capability label in use is never removed or renamed" gains the fold: a label a spec no longer names is
  first replaced on every issue and pull request by every label that spec names, and is removed only once it's on
  nothing.

## Impact

- GitHub, during apply and before the pull request: label edits on 43 troupe-run/troupe issues (43 additions, 59
  removals). No issue is closed, reopened or otherwise changed.
- `tofu/labels/troupe.json`: 13 labels removed, 36 left.
- `openspec/specs/labels/spec.md`, through the delta.
- GitHub, after the owner approves the plan: troupe's `github_issue_labels` changes in place, deleting the 13 labels.
  Nothing else changes.
- #151 is closed by this change's pull request.
