# Design

## Context

See proposal.md for why. The approach is installation-spec-purpose's (2026-10-30), without a description change.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it: without the `Capability:` line, whitespace collapsed. Its keys are sorted.
- The `drift (out of band)` job in `tofu.yml` runs `oob.py` on each run of `main` after CI succeeds, on the 06:00 UTC
  schedule, and by hand. It doesn't wait for an apply.
- `scripts/plan_needed.py` decides whether a pull request needs `plan (pull request)`. Neither `oob/` nor
  `openspec/` is a path OpenTofu reads.

Evidence read on 2026-10-30:

| | |
|---|---|
| `uv run scripts/oob.py` on this branch (2adb29e, = `origin/main`) | one difference: `settings`'s Purpose isn't recorded |
| troupe `main` (efa5105, troupe#203's merge) | `openspec/specs/settings/spec.md`, ``Capability: `cap:settings` `` |
| `purpose()` of that file | exactly #228's quote |
| troupe specs naming `cap:settings` | settings only |
| `oob/troupe-spec-purposes.json` | 26 entries, none for `settings` |
| `tofu/labels/troupe.json` | 36 labels; `cap:settings`: "Named settings with one default each, and how project, user and house levels layer" |
| `plan_needed.py` on `oob/troupe-spec-purposes.json` and the change's files | `plan=false` |
| last `tofu` run on `main` | 40985235730, 01:20 UTC, success, before troupe#203 merged |

The Purpose:

> Gives troupe one seam through which every setting that isn't policy is read, each with a named default and a known
> source, so settings can gain project, user and house levels later without anything else reading a setting its own
> way.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing once this merges.
- `cap:settings`'s description is checked against the Purpose it now covers.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec. A red job is how a missed record gets noticed.
- Changing how troupe asks for the record. troupe#199's line in troupe's project context worked: it's why #228 was
  raised before the merge. The record just landed after it.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read from troupe's `main` through `purpose()`, not copied from #228 or this design, so the record is
what the check compares against. It goes between `scripted-runner` and `stages`, keeping the keys sorted.

### D2. `cap:settings`'s description is kept

"Named settings with one default each, and how project, user and house levels layer" covers each part of the Purpose:
named settings read through one seam, a named default each, and the project, user and house levels to come. `settings`
is the only spec that names the label, so nothing else constrains it. #228's label check says the same.

Alternative: mention "one seam" or "known source" in the description. Rejected: the description says what the label
covers, not how the spec delivers it, and changing it would open a board-description window in the drift job until
the next apply (installation-spec-purpose D4) for no gain.

## Risks / Trade-offs

- [The drift job is red from its next run until this merges] → expected, and it names this record. Merging promptly
  closes it. If a run fails first, re-run its `drift (out of band)` job after the merge, or let the merge's own run
  pass.
- [troupe changes `settings`'s Purpose before this merges] → 2.1 re-runs `oob.py` on the branch, fast-forwarded onto
  `origin/main`, just before the pull request is opened. If it reports a changed Purpose, the record and D2 are
  checked again together.
- [troupe adds another spec before this merges] → 2.1 stops if `oob.py` reports anything else, and the change is
  revised.

## Migration Plan

Nothing is applied: the merge changes no path OpenTofu reads, so `plan (main)` has no changes and `apply (main)` is
skipped. Rolling back is a revert of the pull request, after which the drift job fails again until `settings`'s
Purpose is recorded.
