# Proposal

Issue: #276.

## Why

troupe-run/troupe's change `openai-style-runner` (troupe-run/troupe#297, for troupe#162) adds a main spec,
`openai-runner`. Once it merges, `uv run scripts/oob.py` reports its Purpose as unrecorded, and the `drift (out of
band)` job fails, as it would have for `effects` (#264).

## What Changes

- **The Purpose is recorded** in `oob/troupe-spec-purposes.json`, read through `scripts/oob.py`'s `purpose()`: from
  troupe#297's branch now, and again from troupe's `main` once it merges (design D1).
- **`cap:actor-runners`' description is kept**, checked against the Purpose (design D2).
- **troupe#297 merges first, then this** (design D3): `oob.py` also reports a recorded Purpose with no spec.
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- troupe#297's other spec deltas (`runs`, `config`, `cli`). None of them changes a Purpose, so their records stay.
- Editing troupe-run/troupe's files, or ordering its merge. The owner merges both.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "A capability label says what it covers", "A
description written from a spec records that spec's Purpose" and "A description that may be stale is reported". So
the change sets `skip_specs`, as ollama-runner-spec-purpose did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added (32 → 33).
- `tofu/labels/troupe.json`: unchanged (36 labels). So the plan changes nothing on GitHub, and the board's options
  need no new description.
- The drift job: red from troupe#297's merge until this merges (one unrecorded Purpose).
- #276 is closed by this change's pull request.
