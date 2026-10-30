# Proposal

Issue: #228.

## Why

troupe-run/troupe#203 (for troupe#156, change `mark-config-resolved`) merged troupe's new `settings` spec on
2026-10-30 at 10:49 UTC. Its Purpose isn't recorded here, so `uv run scripts/oob.py` now reports:

```
troupe labels: 'settings' spec's Purpose isn't recorded; check the descriptions of 'cap:settings' against it and record it in oob/troupe-spec-purposes.json
oob: 1 difference(s). Fix GitHub, or update the declaration in oob/.
```

The `drift (out of band)` job hasn't run since the troupe merge. Its next run fails with the same difference: the
next push to `main`, or the 06:00 UTC schedule. #228 asked for the record to land with or before troupe's pull
request. It came after, so the drift job is red from its next run until this merges.

## What Changes

- **The `settings` Purpose is recorded** in `oob/troupe-spec-purposes.json`, read from troupe's `main` through
  `scripts/oob.py`'s `purpose()` (design D1).
- **`cap:settings`'s description is kept**, checked against the Purpose (design D2).
- **No label is added, removed, renamed or redescribed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- troupe's project context. troupe#199 already added the line saying a new spec's Purpose is recorded here, and
  #228 was raised because of it.
- The roadmap board's Capability field. No label or description changes, so no option changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "A description written from a spec records that
spec's Purpose" and "A description that may be stale is reported". So the change sets `skip_specs`, as
installation-spec-purpose and label-troupe-config-specs did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added (26 → 27).
- `tofu/labels/troupe.json`: unchanged (36 labels).
- GitHub: nothing. No path OpenTofu reads changes (`scripts/plan_needed.py` says `plan=false`), so `plan (pull
  request)` is skipped, and `plan (main)` after the merge has nothing to apply.
- The drift job passes on the first run after the merge.
- #228 is closed by this change's pull request.
