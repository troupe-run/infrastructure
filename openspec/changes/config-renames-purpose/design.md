# Design

## Context

See proposal.md for why. The approach is hand-edits-purpose's (2026-11-23): one spec, and no description to change.
troupe#505 hasn't merged yet, so the Purpose is read first from its branch, `config-mv`. Task 1.3 reads it again from
troupe's `main` once #505 has merged, before this is marked ready.

Evidence read on 2026-11-23:

| | |
|---|---|
| troupe#505 | open, head bdd8f124 on `config-mv` |
| `purpose()` of `openspec/specs/config-renames/spec.md` on `config-mv` | exactly #392's quote |
| `config-renames`' Capability line | `` `cap:config` `` |
| `oob/troupe-spec-purposes.json` | no `config-renames` |

The Purpose:

> **config-renames**: Renaming an actor or a runtime as one change, with `troupe config mv` or by moving its files, so
> that its history, the runs recorded under its old name and changes made to it on other branches all follow it to the
> new name.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once this and troupe#505 have merged.
- The label the new spec names has a description checked against its Purpose.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec.
- Any other entry in the file.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read through `purpose()` from `openspec/specs/config-renames/spec.md`, not copied from #392 or this
design, so the record is what the check compares against. `config-renames` goes between `config-hand-edits` and
`docs-publishing`, keeping the keys sorted.

### D2. The description of `cap:config` is kept

| Label | Description (unchanged) | What the spec adds, already covered |
|---|---|---|
| `cap:config` | `A theatre's config as events with lineage, merged across branches, and its kinds: actors, runtimes` | a rename is a config event, merged across branches |

Renaming is part of config's events and their merge, which the label already describes.

## Risks / Trade-offs

- [troupe changes the Purpose again before #505 merges] → task 1.3 runs `oob.py` against troupe's live `main` after
  #505 merges, and would report the difference.
