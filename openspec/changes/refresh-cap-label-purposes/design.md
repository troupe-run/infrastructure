# Design

## Context

See proposal.md for why. What shapes the approach:

- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource, so a description change is an in-place update on the next apply. It doesn't delete or recreate the label
  and doesn't touch the issues that carry it.
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
| troupe PRs for `release-automation` | none |
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

**Non-Goals:**
- Re-reading the other 13 labelled specs. #29 recorded that they matched on 2026-10-13, and `oob.py` would report any
  that had changed since.
- Re-labelling troupe issues. Neither label's scope changes.

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

## Risks / Trade-offs

- [troupe changes a spec again before this merges] → `oob.py` is run on the branch before the pull request opens
  and on `main` after the apply. A new difference is reported on #29, not folded in silently.
- [The plan shows more than two descriptions changing, for example drift made by hand] → The plan is read before the
  pull request opens. Anything beyond the two in-place updates is reported to the owner.
- [`release-automation` archives while this is open] → `cap:releases` is still a separate change: it creates a label
  and labels troupe#23, which is a different plan and a different follow-up.

## Migration Plan

The owner approves the pull request's plan. After the merge, the owner approves the `apply` job, which updates the
two descriptions. Rolling back is reverting the commit: the next apply puts the old descriptions back, and nothing is
deleted.

## Open Questions

- **Which issue the pull request closes.** The guard's `pr-closes-issue` rule needs `Closes #<n>` in the pull
  request, but #29 is a standing ticket that stays open until `cap:releases` is done. This changes only the pull
  request's body and the follow-up comment, not the work. The options:
  - **(a) Recommended:** close #29 with this pull request and open a new issue for `cap:releases`, triggered by
    troupe-run/troupe#23's archive. Under `pr-closes-issue`, every update to a standing ticket needs an issue it can
    close anyway, so it's simplest for each update to have its own.
  - (b) Open a narrow issue for these two labels, close that one, and tick #29's boxes in a comment, so #29 stays
    open as the standing list.
