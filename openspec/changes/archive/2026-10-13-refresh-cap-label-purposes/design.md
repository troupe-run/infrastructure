# Design

## Context

See proposal.md for why. What shapes the approach:

- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource, so a description change is an in-place update on the next apply. It doesn't delete or recreate the label
  and doesn't touch the issues that carry it. A new name is a label created; it exists on GitHub only once the owner
  approves the apply, so labelling an issue with it has to wait until then.
- `oob/troupe-spec-purposes.json` maps each `cap:<name>` with a troupe spec to that spec's Purpose, whitespace
  collapsed (`scripts/oob.py`'s `purpose()`), sorted by label name (cap-label-descriptions D1). `oob/README.md` says
  to review the description against the new text when a Purpose changes, and to update both files together.
- `scripts/tests/test_labels.py` (run by `scripts/check.py`) refuses a description over 100 characters, or one that
  only repeats the name.

Evidence read on 2026-10-13:

| | |
|---|---|
| `uv run scripts/oob.py` on `main` | 2 differences: `cap:platform` Purpose changed; `cap:protocol` has no recorded Purpose |
| troupe's spec folders on `main` (15) | the 14 from #26, plus `protocol` (troupe-run/troupe#72) |
| troupe's `openspec/changes/` on `main` | `archive` only, so `release-automation` isn't there |
| troupe PRs or branches for `release-automation` | none |
| What defines `releases` | troupe-run/troupe#23's body: releases, versions and the changelog derived from Conventional Commits through a release PR |
| troupe#23's labels | `cap:infrastructure` |
| Issues carrying `cap:platform` | 12 |
| Issues carrying `cap:protocol` | 13, including plugin transports (#37, #57), the plugin SDK (#58) and the config model (#60) |

The two Purposes on troupe's `main`, whitespace collapsed:

- **platform:** "The single seam for OS-specific behaviour, so that troupe's file writes, locking, child processes,
  interrupts, directory watching and path display behave the same on Linux, macOS and Windows. Later: daemon IPC."
- **protocol:** "The rules every schema troupe publishes follows, in `protocol/` and in each plugin: JSON Schema that
  is strict, so every value troupe reads or writes has a known shape that tools, editors and other languages can
  check."

## Goals / Non-Goals

**Goals:**
- `oob.py` reports no difference for troupe's labels once this merges.
- Both descriptions say what the label covers today, checked against the spec.
- troupe's release work has a label to be filed under, and #29's list is done when this merges.

**Non-Goals:**
- Re-reading the other 13 labelled specs. #29 recorded that they matched on 2026-10-13, and `oob.py` would report any
  that had changed since.
- Re-labelling troupe issues other than #23. Neither changed label's scope changes.

## Decisions

### D1. `cap:platform`: name what's built, drop IPC

Description: `The one seam for OS-specific behaviour: files, locks, processes, interrupts, file watching, paths` (97
characters). It keeps the current form ("The one seam for OS-specific behaviour: …"), follows the spec's order, says
"interrupts" where the spec says interrupts rather than "signals", and drops IPC, which the Purpose lists under
"Later". A description can't list everything in 100 characters, and something planned is the thing to leave out.

Alternative: keep the description and only refresh the record, which #29 says is enough. Rejected because the
description would keep naming IPC, which isn't built, and would omit path display, which is. The edit costs one line
in the same file the plan already reads.

### D2. `cap:protocol`: keep the scope, add "strict" and "each plugin"

Description: `Strict, language-neutral JSON Schema contracts in protocol/ and each plugin, for every surface` (94
characters). The current description, "Language-neutral JSON Schema contracts in protocol/, shared by every language
and surface", was written from troupe's glossary before the spec existed. The spec adds two things: every schema is
strict, and plugins' schemas are covered too. Both go in, and "language-neutral" stays.

Alternative: write the description from the Purpose alone, for example "The rules every schema troupe publishes
follows: strict JSON Schema …". Rejected because the label already covers more than the rules: 13 issues carry it,
including plugin transports and the plugin SDK. A description narrowed to the schema rules would misdescribe the
issues already filed under it. The spec's Purpose is about schemas, and the label is the capability's, so the
description says both.

### D3. The record is the spec's text, verbatim

Each recorded Purpose is the spec's `## Purpose` section as `oob.py`'s `purpose()` reads it, whitespace collapsed,
copied from `gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md` rather than from #29's body.
`oob.py` compares against exactly that, so it's the only text that makes the check pass. `cap:protocol` goes in name
order, after `cap:policy`.

### D4. `cap:releases` before its spec, its Purpose recorded when the spec lands

`{"name": "cap:releases", "color": "1D76DB", "description": "Versions, changelogs and releases, derived from
Conventional Commits through a release PR"}` (89 characters), inserted after `cap:protocol` so the file stays sorted.
The description is #29's, and troupe#23's body defines the capability it describes, so it isn't the guess the `TBD`
rule guards against. The labels spec lets a label come before its spec, and `oob.py` skips a label with no spec.

No Purpose is recorded for it. There's no spec text to copy, and `oob.py` reports a recorded Purpose with no spec
(`scripts/oob.py`, `stale_descriptions`). When troupe#23's change archives and `openspec/specs/releases/` reaches
troupe's `main`, `oob.py` reports "`cap:releases` description hasn't been checked against its spec's Purpose". That
report is the trigger to record the Purpose and review the description, so nothing has to remember it.

troupe#23 gets the label after the apply, with `gh issue edit --add-label`, as #29 asks. It keeps
`cap:infrastructure`. This is a write to troupe's issue metadata, not its files, as in runs-and-client-protocol-labels
D2.

Alternative: wait for troupe#23 to archive, as #29 first said. Rejected: it holds #29 open for a one-line addition
that is safe to make now, and troupe#23's work has no label to be filed under until then.

## Risks / Trade-offs

- [troupe changes a spec again before this merges] → `oob.py` is run on the branch before the pull request opens
  and on `main` after the apply. A new difference is reported on #29, not folded in silently.
- [The plan shows more than two descriptions changing, for example drift made by hand] → The plan is read before the
  pull request opens. Anything beyond the two in-place updates is reported to the owner.
- [troupe names the spec folder something other than `releases`] → `oob.py` reports that folder as unlabelled. By
  then troupe#23 carries `cap:releases`, so a rename falls under "A capability label in use is never removed or
  renamed": the fix is a new label, with the old one kept. #29 names the spec `releases`, so this is unlikely.
- [troupe#23's change rewrites the Purpose before it archives] → No effect here: the Purpose is recorded from the spec
  that lands, when `oob.py` asks for it (D4).
- [`release-automation` archives while this is open] → `oob.py` reports `cap:releases` as unrecorded on the branch.
  Its Purpose is recorded here then, from troupe's `main`, the same way as D3.

## Migration Plan

The owner approves the pull request's plan. After the merge, the owner approves the `apply` job, which creates
`cap:releases` and updates the two descriptions. Then troupe#23 is labelled (D4). Rolling back is reverting the
commit: the next apply puts the old descriptions back and deletes `cap:releases`, which takes it off troupe#23.
