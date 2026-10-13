# Proposal

Issue: #29, the standing ticket that keeps troupe's `cap:` labels in step with troupe's specs. This change does all of
it: `cap:platform` from the ticket's list, `cap:protocol`, which drifted after the ticket was written, and
`cap:releases`, declared ahead of its spec.

## Why

`scripts/oob.py` reports two differences for troupe's labels on 2026-10-13:

- `cap:platform`: troupe-run/troupe#74 (`watch-event-segments`, merged 10:52) rewrote the platform spec's Purpose.
  The recorded Purpose is stale, and the label's description still lists IPC, which the spec now says is "Later".
- `cap:protocol`: troupe-run/troupe#72 (`strict-schemas`, merged 11:41) added `openspec/specs/protocol/`. The label
  already existed with a description written from troupe's glossary, so no Purpose is recorded for it.

#29's sweep ran before #72 merged, which is why it names only `cap:platform`. Until both are fixed, `oob.py` can't
report a clean result for troupe's labels, and a later drift would be hidden among these two.

troupe-run/troupe#23 (`release-automation`) will add a `releases` spec, and there's no label to file its work under.
The labels spec lets a label come before its spec, so adding `cap:releases` now finishes #29 instead of holding it
open for a one-line addition.

## What Changes

- **`cap:platform`'s recorded Purpose** in `oob/troupe-spec-purposes.json` is replaced with the spec's Purpose on
  troupe's `main`, whitespace collapsed.
- **`cap:platform`'s description** in `tofu/labels/troupe.json` changes to match that Purpose: it drops IPC, which
  is planned rather than built, and names interrupts and paths (design D1). #29 calls this edit optional.
- **`cap:protocol`'s Purpose is recorded** in `oob/troupe-spec-purposes.json`, verbatim with whitespace collapsed.
- **`cap:protocol`'s description** gets the spec's two additions, "strict" and "each plugin", and keeps its existing
  wording otherwise, because 13 troupe issues already carry the label for that scope (design D2).
- **`cap:releases` is added** to `tofu/labels/troupe.json`, colour `1D76DB`, with #29's description "Versions,
  changelogs and releases, derived from Conventional Commits through a release PR" (design D4).
- **troupe-run/troupe#23 is labelled `cap:releases`** once the apply creates the label. It keeps `cap:infrastructure`.
- **No label is removed or renamed.**

Out of scope:
- **Recording `cap:releases`'s Purpose.** troupe has no `releases` spec yet, so there's no Purpose to record, and
  `oob.py` reports a recorded Purpose with no spec. `oob.py` asks for it once the spec lands (design D4).
- `scripts/oob.py`, the labels spec and the workflow's labels, which #26 settled and #29 rules out.
- Any change to troupe-run/troupe's files. Its only issue change is the label on #23.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a data change under the existing `labels` requirements "troupe's capability labels are declared here",
"A capability label says what it covers", "A description written from a spec records that spec's Purpose" and "A
description that may be stale is reported", so the change sets `skip_specs: true`.

## Impact

- `tofu/labels/troupe.json`: two descriptions changed and one label added, 39 → 40.
- `oob/troupe-spec-purposes.json`: one entry changed, one added.
- GitHub, after the owner approves the plan: `cap:releases` created on troupe-run/troupe, and two label descriptions
  updated in place. Changing a description doesn't touch the issues that carry the label.
- troupe-run/troupe#23: `cap:releases` added. From then on the label falls under "A capability label in use is never
  removed or renamed".
- `scripts/oob.py` reports nothing for troupe's labels once this merges, until troupe's next spec change.
- #29 is closed by this change's pull request.
