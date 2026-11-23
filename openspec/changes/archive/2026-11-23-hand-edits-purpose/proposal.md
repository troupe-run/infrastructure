# Proposal

Issue: #382.

## Why

troupe-run/troupe#490 (the hand-edit sweep, for troupe#119) added a main spec, `config-hand-edits`, and merged as
10c2ed4. Since then `uv run scripts/oob.py` reports its Purpose as unrecorded, and the `drift (out of band)` job
fails, as it did before mistralrs-runner-spec-purpose (#307).

## What Changes

- **The Purpose is recorded** in `oob/troupe-spec-purposes.json`, read through `scripts/oob.py`'s `purpose()` from
  troupe's `main` (design D1).
- **The descriptions of `cap:config`, `cap:projections` and `cap:lineage` are kept**, checked against the Purpose
  (design D2).
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- Other entries in the same file. troupe#490 changes no other spec's Purpose (task 1.3 checks this with `oob.py`).
- Editing troupe-run/troupe's files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "A capability label says what it covers", "A
description written from a spec records that spec's Purpose" and "A description that may be stale is reported". So
the change sets `skip_specs`, as mistralrs-runner-spec-purpose did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added (35 → 36).
- `tofu/labels/troupe.json`: unchanged. So the plan changes nothing on GitHub.
- The drift job: red from troupe#490's merge until this merges (one unrecorded Purpose).
- #382 is closed by this change's pull request.
