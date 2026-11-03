# Proposal

Issue: #264.

## Why

troupe-run/troupe's change `declared-effects` (troupe-run/troupe#273, for troupe#241) adds a main spec, `effects`.
Once it merges, `uv run scripts/oob.py` reports its Purpose as unrecorded, and the `drift (out of band)` job fails, as
it did for `plugin-sdk` and `runner-tools` (#262). The spec is the first to name `cap:effects`, whose description says
the declaration is "enforced by its stage", while the spec is about what happens before any stage enforces it.

## What Changes

- **The Purpose is recorded** in `oob/troupe-spec-purposes.json`, read through `scripts/oob.py`'s `purpose()`: from
  troupe#273's branch now, and again from troupe's `main` once it merges (design D1).
- **`cap:effects`'s description is reworded** to say the declaration is applied by its runner and audited, as well as
  enforced by a stage, using #264's wording (design D2). It's for the owner to confirm, in review and in the plan.
- **`cap:config`'s description is kept**, checked against the Purpose (design D2).
- **troupe#273 merges first, then this** (design D3), as #262's change did: `oob.py` also reports a recorded Purpose
  with no spec.
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- troupe#273's other spec deltas. None of them changes a Purpose, so their records stay.
- Editing troupe-run/troupe's files, or ordering its merge. The owner merges both.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "A capability label says what it covers", "A
description written from a spec records that spec's Purpose" and "A description that may be stale is reported". So
the change sets `skip_specs`, as sdk-spec-purposes did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added (29 → 30).
- `tofu/labels/troupe.json`: one description changed (36 labels, unchanged).
- GitHub, after the owner approves the plan: `cap:effects` updated in place on troupe-run/troupe, then the troupe
  roadmap board's `effects` option given the same description by `board descriptions (main)` (spec: labels).
- The drift job: red from troupe#273's merge until this merges (one unrecorded Purpose), then red on the board's
  `effects` option until the apply and `board descriptions (main)` have run (design D3).
- #264 is closed by this change's pull request.
