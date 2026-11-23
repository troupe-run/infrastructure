# Design

## Context

See proposal.md for why. The approach is mistralrs-runner-spec-purpose's (2026-11-15): one spec, and no description
to change. Here troupe's pull request has already merged, so the Purpose is read from troupe's `main` from the start,
as #276's design D3 asks.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it: without the `Capability:` line, whitespace collapsed. Its keys are sorted.
- `stale_descriptions()` reports a spec whose Purpose isn't recorded, one whose Purpose has changed, and a record
  with no spec.

Evidence read on 2026-11-23:

| | |
|---|---|
| troupe#490 | merged as 10c2ed4; troupe's `main` at 5e3ed97 |
| `purpose()` of `openspec/specs/config-hand-edits/spec.md` on `main` | exactly #382's quote |
| `config-hand-edits`' Capability line | `` `cap:config`, `cap:projections`, `cap:lineage` `` |
| `oob/troupe-spec-purposes.json` | 35 entries, no `config-hand-edits` |

The Purpose:

> **config-hand-edits**: Reads a person's edits to the config files under `.troupe/` back into config, recording
> each meaningful one as a change with lineage, and never mistaking a half-saved or invalid file for a removal.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once this has merged.
- Each label the new spec names has a description checked against its Purpose.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec.
- Any other entry in the file.

## Decisions

### D1. The record is the spec's text on troupe's `main`, read through `purpose()`

The entry is read through `purpose()` from `openspec/specs/config-hand-edits/spec.md` on troupe's `main`, not
copied from #382 or this design, so the record is what the check compares against. `config-hand-edits` goes between
`config-files` and `docs-publishing`, keeping the keys sorted.

### D2. The descriptions: all three labels are kept

| Label | Description (unchanged) | What the spec adds, already covered |
|---|---|---|
| `cap:config` | `A theatre's config as events with lineage, merged across branches, and its kinds: actors, runtimes` | hand edits become config events with lineage |
| `cap:projections` | `Read models folded from events, such as config files, run status and logs` | the config files are the projection a person edits; reading them back is that projection's other direction |
| `cap:lineage` | `What every event records about itself: who, through what, when, why, change, cause, approvals` | each meaningful edit is recorded with lineage |

The spec is a new part of config's projection to files, which these labels already describe; none of them needs
wording about hand edits to say what it covers.

## Risks / Trade-offs

- [troupe changes the Purpose again before this merges] → task 1.3 runs `oob.py` against troupe's live `main` after
  the last rebase, and would report the difference.
- [Another spec-record change edits the same file] → each adds or removes only its own line; a rebase is a one-line
  conflict at most.
