# Proposal

Issue: #224.

## Why

troupe-run/troupe#192 (for troupe#144) merged troupe's `installation` spec on 2026-10-29. Its Purpose isn't recorded
here, so the `drift (out of band)` job has failed on every run since (runs 40869485951 and 40872692308):

```
troupe labels: 'installation' spec's Purpose isn't recorded; check the descriptions of 'cap:development', 'cap:user-docs' against it and record it in oob/troupe-spec-purposes.json
oob: 1 difference(s). Fix GitHub, or update the declaration in oob/.
```

The spec names two labels. `cap:user-docs`'s description covers the documented install. `cap:development`'s
description doesn't mention installing.

Nothing in troupe said a new spec needs this. troupe's `openspec/config.yaml` sends a *new label* through #152, but
`installation` used existing labels, so nobody looked here until the job failed after the merge. `oob/README.md`
already says a new troupe spec gets its Purpose recorded, but nobody working in troupe reads it.

## What Changes

- **The `installation` Purpose is recorded** in `oob/troupe-spec-purposes.json`, read from troupe's `main` through
  `scripts/oob.py`'s `purpose()` (design D1).
- **`cap:development`'s description is widened** to say "installed" (owner, 2026-10-30, design D2). The label keeps
  its name and colour.
- **`cap:user-docs`'s description is kept**, checked against the Purpose (design D2).
- **A troupe issue is raised**, on the board, to add a line to troupe's project context: every new troupe spec needs
  its Purpose recorded in infrastructure, in a pull request that lands with or before it (owner, 2026-10-30, design
  D3).
- **No label is added, removed or renamed.**

Out of scope:
- `scripts/oob.py`, `oob/README.md` and `docs/standard-changes.md`, whose rules this change follows unchanged.
- Editing troupe-run/troupe's files. Changes to a product repo's files arrive as its own pull requests, so this
  change raises the issue and stops there.
- The roadmap board's Capability field. No label is added, so no option is needed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "A capability label says what it covers", "A
description written from a spec records that spec's Purpose" and "A description that may be stale is reported". So
the change sets `skip_specs`, as label-troupe-config-specs did.

## Impact

- `oob/troupe-spec-purposes.json`: one entry added (25 → 26).
- `tofu/labels/troupe.json`: one description changed (36 labels, unchanged).
- GitHub, after the owner approves the plan: `cap:development`'s description updated in place on troupe-run/troupe,
  then the troupe roadmap board's `development` option given the same description by `board descriptions (main)`
  (spec: labels, "An approved apply gives the board's options their labels' descriptions").
- A new troupe-run/troupe issue, on the troupe roadmap board.
- The drift job passes again once the apply and the board's description have run. Until then it reports the
  `development` option's description differing from `cap:development`'s (design D4).
- #224 is closed by this change's pull request.
