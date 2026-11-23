# Proposal

Issue: #392.

## Why

troupe-run/troupe#505 (`config mv` and hand moves, for troupe#138) adds a main spec, `config-renames`. It's split out
of `config`, which would otherwise pass the size gate's limit (owner, 2026-11-23). Once #505 merges,
`uv run scripts/oob.py` reports its Purpose as unrecorded and the `drift (out of band)` job fails, as it did for
config-hand-edits (#382).

## What Changes

- **The Purpose is recorded** in `oob/troupe-spec-purposes.json`, read through `scripts/oob.py`'s `purpose()` (design
  D1).
- **The description of `cap:config` is kept**, checked against the Purpose (design D2).
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- Other entries in the same file. troupe#505 changes no other spec's Purpose (task 1.3 checks this with `oob.py`).
- Editing troupe-run/troupe's files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements, so the change sets `skip_specs`, as
hand-edits-purpose did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added.
- `tofu/labels/troupe.json`: unchanged, so the plan changes nothing on GitHub.
- The drift job is red from troupe#505's merge until this merges (one unrecorded Purpose). This merges promptly after.
- #392 is closed by this change's pull request.
