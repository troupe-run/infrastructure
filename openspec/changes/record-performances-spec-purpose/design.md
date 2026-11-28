# Design

## Context

See proposal.md for why. The approach is record-gates-spec-purpose's (2026-11-27): one spec, read straight from
troupe's `main`, since troupe#545 has merged. Unlike that change, there's no milestone to update.

Evidence read on 2026-11-28:

| | |
|---|---|
| troupe#545 | merged 2026-11-28; troupe's `main` at 4e77cc28 |
| `purpose()` of `openspec/specs/performances/spec.md` on `main` | exactly #425's quote |
| `performances`' Capability line | `` `cap:runs`, `cap:lineage` `` |
| `oob/troupe-spec-purposes.json` | 38 entries, no `performances` |

The Purpose:

> **performances**: Records every perform as a performance: one run of your process, with its own id, its start and
> its end, whose steps are runs, so that whatever a perform caused can be found from the performance, and a
> performance id names its run.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once this merges.
- The labels the new spec names have descriptions checked against its Purpose.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec.
- Any other Purpose entry, or any label's description.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read through `purpose()` from `openspec/specs/performances/spec.md` on troupe's `main`. It isn't copied
from #425 or from this design, so the record is exactly what the check compares against. `performances` goes between
`openai-runner` and `platform`, keeping the keys sorted.

### D2. The descriptions of `cap:runs` and `cap:lineage` are kept

| Label | Description (unchanged) | What the spec adds, already covered |
|---|---|---|
| `cap:runs` | `Recording each run of an actor with lineage, and reading runs back: status, logs, follow` | a performance is recorded around each perform's run, and read back through the same commands |
| `cap:lineage` | `What every event records about itself: who, through what, when, why, change, cause, approvals` | every event of a performance or its runs names the performance |

`cap:runs` already covers recording runs and reading them back, and a performance is the record around a perform's
runs. `cap:lineage`'s list isn't exhaustive: it doesn't name `vcs` or `stage` either. Adding "performance" would take
it from 93 characters past the 100-character limit, for no gain in accuracy.

## Risks / Trade-offs

- **The drift job stays red until this merges.** That window is accepted (owner, 2026-10-30), since troupe merges
  first so this record can be read from its `main`.
