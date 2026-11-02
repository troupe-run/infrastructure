# Proposal

Issue: #262.

## Why

troupe-run/troupe's change `runner-sdk` (troupe-run/troupe#268, for troupe#240) adds two main specs, `plugin-sdk` and
`runner-tools`. Once it merges, `uv run scripts/oob.py` reports each one's Purpose as unrecorded, and the
`drift (out of band)` job fails, as it did for `installation` (#224) and `settings` (#228). The specs also name
`cap:plugins` and `cap:actor-runners`, whose descriptions don't yet cover the plugin SDK or a runner's tool calls.

troupe#268 is still a draft. troupe#199's line in troupe's project context is why #262 was raised before the merge.

## What Changes

- **Both Purposes are recorded** in `oob/troupe-spec-purposes.json`, read through `scripts/oob.py`'s `purpose()`:
  from troupe#268's branch now, and again from troupe's `main` once it merges (design D1).
- **`cap:plugins`'s description is widened** to name the plugin SDK (owner, 2026-11-02, choosing #262's wording;
  design D2).
- **`cap:actor-runners`'s description is widened** to name a runner's tool calls (owner, 2026-11-02, choosing
  #262's wording; design D2).
- **`cap:protocol`'s description is kept**, checked against `plugin-sdk`'s Purpose (design D2).
- **troupe#268 merges first, then this** (design D3). #262 asks for "with or before", but `oob.py` also reports a
  recorded Purpose with no spec, so merging this first only moves the red window.
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- troupe#268's other spec deltas (`installation`, `quality-check`, `scripted-runner`). None of them changes a
  Purpose, so their records stay.
- Editing troupe-run/troupe's files, or ordering its merge. The owner merges both.
- The App's `pull_requests: read`, which `oob.py` reports today. #261 (`milestone-list-token`) declares it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "A capability label says what it covers", "A
description written from a spec records that spec's Purpose" and "A description that may be stale is reported". So
the change sets `skip_specs`, as installation-spec-purpose and settings-spec-purpose did.

## Impact

- `oob/troupe-spec-purposes.json`: two entries added (27 → 29).
- `tofu/labels/troupe.json`: two descriptions changed (36 labels, unchanged).
- GitHub, after the owner approves the plan: `cap:plugins` and `cap:actor-runners` updated in place on
  troupe-run/troupe, then the troupe roadmap board's `plugins` and `actor-runners` options given the same
  descriptions by `board descriptions (main)` (spec: labels).
- The drift job: red from troupe#268's merge until this merges (two unrecorded Purposes), then red on the two board
  options until the apply and `board descriptions (main)` have run (design D3, D4).
- #262 is closed by this change's pull request.
