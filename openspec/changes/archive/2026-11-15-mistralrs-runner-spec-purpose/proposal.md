# Proposal

Issue: #307.

## Why

troupe-run/troupe's change `in-process-runner` (for troupe#414, pull request troupe#422) adds a main spec,
`mistralrs-runner`. Once it merges, `uv run scripts/oob.py` reports its Purpose as unrecorded, and the
`drift (out of band)` job fails, as it would have for `lm-studio-runner` (#296).

## What Changes

- **The Purpose is recorded** in `oob/troupe-spec-purposes.json`, read through `scripts/oob.py`'s `purpose()`: from
  troupe's `in-process-runner` branch now, and again from troupe's `main` once it merges (design D1).
- **`cap:actor-runners`' description is kept**, checked against the Purpose (design D2).
- **troupe's pull request merges first, then this** (design D3): `oob.py` also reports a recorded Purpose with no
  spec.
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- The troupe change's other spec deltas (`runtimes`, `runner-protocol`, `cli`). None of them changes a
  Purpose, so their records stay.
- Other entries in the same file. troupe#413 removes `lm-studio-runner`'s spec and troupe#415 adds the Anthropic
  runner's, each through its own infrastructure change. This one adds its own entry and touches no other.
- Editing troupe-run/troupe's files, or ordering its merge. The owner merges both.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "A capability label says what it covers", "A
description written from a spec records that spec's Purpose" and "A description that may be stale is reported". So
the change sets `skip_specs`, as lm-studio-runner-spec-purpose did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added (34 → 35).
- `tofu/labels/troupe.json`: unchanged. So the plan changes nothing on GitHub.
- The drift job: red from troupe's `in-process-runner` merge until this merges (one unrecorded Purpose).
- #307 is closed by this change's pull request.
