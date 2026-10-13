# Proposal

Issue: #29, the standing ticket that keeps troupe's `cap:` labels in step with troupe's specs. This change does the
items that are ready now: `cap:platform` from the ticket's list, and `cap:protocol`, which drifted after the ticket
was written. `cap:releases` waits for its spec to reach troupe's `main` (see Out of scope).

## Why

`scripts/oob.py` reports two differences for troupe's labels on 2026-10-13:

- `cap:platform`: troupe-run/troupe#74 (`watch-event-segments`, merged 10:52) rewrote the platform spec's Purpose.
  The recorded Purpose is stale, and the label's description still lists IPC, which the spec now says is "Later".
- `cap:protocol`: troupe-run/troupe#72 (`strict-schemas`, merged 11:41) added `openspec/specs/protocol/`. The label
  already existed with a description written from troupe's glossary, so no Purpose is recorded for it.

#29's sweep ran before #72 merged, which is why it names only `cap:platform`. Until both are fixed, `oob.py` can't
report a clean result for troupe's labels, and a later drift would be hidden among these two.

## What Changes

- **`cap:platform`'s recorded Purpose** in `oob/troupe-spec-purposes.json` is replaced with the spec's Purpose on
  troupe's `main`, whitespace collapsed.
- **`cap:platform`'s description** in `tofu/labels/troupe.json` changes to match that Purpose: it drops IPC, which
  is planned rather than built, and names interrupts and paths (design D1). #29 calls this edit optional.
- **`cap:protocol`'s Purpose is recorded** in `oob/troupe-spec-purposes.json`, verbatim with whitespace collapsed.
- **`cap:protocol`'s description** gets the spec's two additions, "strict" and "each plugin", and keeps its existing
  wording otherwise, because 13 troupe issues already carry the label for that scope (design D2).
- **No label is added, removed or renamed.** The plan updates two descriptions in place and changes nothing else.

Out of scope:
- **`cap:releases`.** troupe-run/troupe#23 (`release-automation`) hasn't opened a pull request, and troupe's `main`
  has no `openspec/specs/releases/` and no `openspec/changes/release-automation/`. #29 says to add the label when
  that change archives. It stays on #29's list for a later change.
- `scripts/oob.py`, the labels spec and the workflow's labels, which #26 settled and #29 rules out.
- Any change to troupe-run/troupe's files or issues.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a data change under the existing `labels` requirements "A capability label says what it covers", "A
description written from a spec records that spec's Purpose" and "A description that may be stale is reported", so
the change sets `skip_specs: true`.

## Impact

- `tofu/labels/troupe.json`: two descriptions changed, still 39 labels.
- `oob/troupe-spec-purposes.json`: one entry changed, one added.
- GitHub, after the owner approves the plan: two label descriptions updated on troupe-run/troupe. Changing a
  description doesn't touch the issues that carry the label.
- `scripts/oob.py` reports nothing for troupe's labels once this merges, until troupe's next spec change.
- #29 stays open for `cap:releases` (design, Open Questions).
