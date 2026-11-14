# Proposal

Issue: #305.

## Why

troupe-run/troupe's change `remove-lm-studio` (for troupe#413) retires the `lm-studio-runner` spec, so archive deletes
`openspec/specs/lm-studio-runner/`. Once it merges, `uv run scripts/oob.py` reports a recorded Purpose with no spec,
and the `drift (out of band)` job fails.

## What Changes

- **The `lm-studio-runner` record is removed** from `oob/troupe-spec-purposes.json` (design D1).
- **`cap:actor-runners`' description is kept** (design D2): it never named LM Studio.
- **troupe's pull request merges first, then this** (design D3).
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- The troupe change's other spec deltas (`runtimes`, `config`, `cli`, `client-protocol`, `runs`, `installation`,
  `releases`, `runner-protocol`, `quality-check`). None changes a Purpose, so their records stay.
- Other entries in the same file. troupe#415 (#303) and troupe#414 add their own entries through their own changes.
  This one removes its own entry and touches no other.
- Editing troupe-run/troupe's files, or ordering its merge. The owner merges both.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements ("A description that may be stale is reported"),
so the change sets `skip_specs`, as lm-studio-runner-spec-purpose and anthropic-runner-spec-purpose did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry removed (34 → 33, before #303 or troupe#414's entries land).
- `tofu/labels/troupe.json`: unchanged. So the plan changes nothing on GitHub.
- The drift job: red from troupe's `remove-lm-studio` merge until this merges (one record with no spec).
- #305 is closed by this change's pull request.
