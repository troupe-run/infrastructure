# Proposal

Issue: #425.

## Why

troupe-run/troupe#545 (performances, part 1 of troupe#124, closing troupe#546) merged on 2026-11-28 and adds a main
spec, `performances`. Until its Purpose is recorded, `uv run scripts/oob.py` reports it as unrecorded and the
`drift (out of band)` job fails, as it did for gates (#419).

## What Changes

- **The Purpose is recorded** in `oob/troupe-spec-purposes.json`, read through `scripts/oob.py`'s `purpose()` from
  troupe's `main` (design D1).
- **The descriptions of `cap:runs` and `cap:lineage` are kept**, checked against the Purpose (design D2).
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- Other entries in the Purposes file. troupe#545 changes no other spec's Purpose: `cli`, `lineage` and `runs` gain or
  change requirements only (task 1.3 checks this with `oob.py`).
- Editing troupe-run/troupe's files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The edit is data under an existing requirement (the `labels` spec's Purpose record), so the change sets
`skip_specs`, as record-gates-spec-purpose did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added.
- `tofu/labels/troupe.json`: unchanged. Nothing under `tofu/` changes, so no plan is needed.
- The drift job has been red since troupe#545 merged (one unrecorded Purpose). This merges promptly.
- #425 is closed by this change's pull request.
