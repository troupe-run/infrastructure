# Design

## Context

See proposal.md for why. The approach is config-renames-purpose's (2026-11-24): one spec, and no label description to
change. One difference: troupe#531 has already merged, so the Purpose is read straight from troupe's `main`. The
other difference is one milestone description, which the owner added to this change.

Evidence read on 2026-11-27:

| | |
|---|---|
| troupe#531 | merged 2026-11-26; troupe's `main` at a6dc7fa9 |
| `purpose()` of `openspec/specs/gates/spec.md` on `main` | exactly #419's quote |
| `gates`' Capability line | `` `cap:gates`, `cap:cues` `` |
| `oob/troupe-spec-purposes.json` | no `gates` |
| 0.4.0 in `tofu/milestones.json` (key `0.3.0`) | "Gates: a run stops for approval before its work is kept; every gate is manual, and the approver is whoever runs troupe" |

The Purpose:

> **gates**: Decides whether a worktree run's work is kept. Each run passes a gate when it ends, and its actor's
> approvers are tried in order: troupe keeps clean work by itself, and a role it can't act for gets a cue that a person
> answers with approve or reject. Every step is recorded with lineage.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once this merges.
- The labels the new spec names have descriptions checked against its Purpose.
- 0.4.0's description says what the release gives, as troupe-run/troupe#139 asks every milestone's description to.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec.
- Any other Purpose entry, or any other milestone.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read through `purpose()` from `openspec/specs/gates/spec.md` on troupe's `main`. It isn't copied from
#419 or from this design, so the record is exactly what the check compares against. `gates` goes between `flake-hunt`
and `identity`, keeping the keys sorted.

### D2. The descriptions of `cap:gates` and `cap:cues` are kept

| Label | Description (unchanged) | What the spec adds, already covered |
|---|---|---|
| `cap:gates` | `Points where work waits for a decision from the role that owns it` | a run's work waits at its gate for its approvers |
| `cap:cues` | `Open requests addressed to a role, with a brief, raised by gates and escalations` | reaching a person's role raises a cue with a brief |

The labels were written for these capabilities before troupe built them, and the Purpose fits them. Saying that troupe
can approve by itself would make `cap:gates` longer without making it more accurate, since `troupe` is the first
approver of a gate, not a separate thing.

### D3. 0.4.0's new description

> Gates: a run’s approvers decide whether its work is kept; troupe keeps clean work, and the rest waits for whoever
> runs troupe

The old description says what was planned before troupe#62's scoping. The new one says what was built:
- every worktree run that succeeds with changes passes a gate;
- by default troupe keeps clean work, and a conflict (or an actor whose approvers are `[director]`) waits for
  whoever runs troupe.

It keeps the old one's shape ("Gates: …") and its length, so `troupe.run/status/` and the board show it the same way.
Only the `description` changes. The key, title and state stay, so the plan updates the description on each
repository in `repositories` and touches no issue's milestone.

## Risks / Trade-offs

- [troupe changes the Purpose again before this merges] → task 1.3 runs `oob.py` against troupe's live `main` just
  before marking ready, and would report the difference.
- [The plan shows more than the description] → task 2.3 reads the plan, and the change stops if anything else
  appears.
