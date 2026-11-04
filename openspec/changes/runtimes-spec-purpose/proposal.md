# Proposal

Issue: #272.

## Why

troupe-run/troupe's change `runtimes` (troupe-run/troupe#287, for troupe#278) adds a main spec, `runtimes`. Once it
merges, `uv run scripts/oob.py` reports its Purpose as unrecorded, and the `drift (out of band)` job fails, as it did
for `effects` (#264). The spec names `cap:config` and `cap:actor-runners`. Runtimes are config's second kind, and
`cap:config`'s description names only the first: "and the actor, its first kind".

## What Changes

- **The Purpose is recorded** in `oob/troupe-spec-purposes.json`, read through `scripts/oob.py`'s `purpose()`: from
  troupe#287's branch now, and again from troupe's `main` once it merges (design D1).
- **`cap:config`'s description is reworded** to name both kinds, actors and runtimes (design D2). The owner chose this
  wording on 2026-11-04, while the change was proposed.
- **`cap:actor-runners`' description is kept**, checked against the Purpose (design D2).
- **troupe#287 merges first, then this** (design D3), as #264's change did: `oob.py` also reports a recorded Purpose
  with no spec.
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- troupe#287's other spec deltas (`config`, `config-files`, `runner-protocol`, `runs`, `scripted-runner`). None of
  them has a Purpose section, so their records stay.
- `config`'s own Purpose, which still says the actor is "the first kind of config". It stays true, and it's troupe's
  to change.
- Editing troupe-run/troupe's files, or ordering its merge. The owner merges both.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "A capability label says what it covers", "A
description written from a spec records that spec's Purpose" and "A description that may be stale is reported". So
the change sets `skip_specs`, as effects-spec-purpose did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added (30 → 31).
- `tofu/labels/troupe.json`: one description changed (36 labels, unchanged).
- GitHub, after the owner approves the plan: `cap:config` updated in place on troupe-run/troupe, then the troupe
  roadmap board's `config` option given the same description by `board descriptions (main)` (spec: labels).
- The drift job: red from troupe#287's merge until this merges (one unrecorded Purpose), then red on the board's
  `config` option until the apply and `board descriptions (main)` have run (design D3).
- #272 is closed by this change's pull request.
