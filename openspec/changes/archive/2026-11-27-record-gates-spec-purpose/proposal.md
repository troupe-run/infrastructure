# Proposal

Issue: #419.

## Why

troupe-run/troupe#531 (gates, for troupe#62) merged on 2026-11-26 and adds a main spec, `gates`. Until its Purpose is
recorded, `uv run scripts/oob.py` reports it as unrecorded and the `drift (out of band)` job fails, as it did for
config-renames (#392). The same work also made the 0.4.0 milestone's description wrong: it says "every gate is
manual". Under troupe#62's decisions, troupe keeps clean work by itself, and only the rest waits for a person. The
owner asked for that line to change in this same change (2026-11-27).

## What Changes

- **The Purpose is recorded** in `oob/troupe-spec-purposes.json`, read through `scripts/oob.py`'s `purpose()` from
  troupe's `main` (design D1).
- **The descriptions of `cap:gates` and `cap:cues` are kept**, checked against the Purpose (design D2).
- **0.4.0's description** in `tofu/milestones.json` says what the release gives now (design D3).
- **No label is added, removed or renamed, and no milestone is added, removed or renumbered.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- Other entries in the Purposes file. troupe#531 changes no other spec's Purpose (task 1.3 checks this with `oob.py`).
- Any other milestone's description.
- Editing troupe-run/troupe's files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Both edits are data under existing requirements (the `labels` spec's Purpose record and the `milestones`
spec's declarations), so the change sets `skip_specs`, as config-renames-purpose did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added.
- `tofu/labels/troupe.json`: unchanged.
- `tofu/milestones.json`: one description changed. The plan updates the 0.4.0 milestone's description in each
  repository that declares it, and the apply waits for the owner's approval as usual.
- The drift job has been red since troupe#531 merged (one unrecorded Purpose). This merges promptly.
- #419 is closed by this change's pull request.
