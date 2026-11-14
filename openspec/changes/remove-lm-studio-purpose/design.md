# Design

## Context

See proposal.md for why. This undoes lm-studio-runner-spec-purpose (2026-11-12), the change that recorded the entry.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it. Its keys are sorted.
- `stale_descriptions()` reports a spec whose Purpose isn't recorded, one whose Purpose has changed, **and a record
  with no spec**, so the record has to go once troupe's spec does.

Evidence read on 2026-11-14:

| | |
|---|---|
| troupe's `remove-lm-studio` change | proposed on branch `remove-lm-studio`. Removes every requirement of `lm-studio-runner` with `retire_capabilities: true`; its other deltas change no Purpose |
| `oob/troupe-spec-purposes.json` | 34 entries, `lm-studio-runner` among them (35 once #303 landed, before the rebase) |
| other mentions of LM Studio in this repository | none outside the archive and that entry |

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once troupe's `remove-lm-studio` change and this have merged.

**Non-Goals:**
- Making the drift job tolerate a record with no spec.
- Any other entry, including #303's `anthropic-runner` and troupe#414's.

## Decisions

### D1. Only the one line goes

The `lm-studio-runner` line is deleted, and nothing else in the file changes: no re-sorting, no reformatting.

### D2. The description: `cap:actor-runners` is kept

`Running an actor through a runner: launch, limits, cancel, its tool calls, and one trusted outcome` names no runner,
and still describes every runner spec left (`claude-code-runner`, `ollama-runner`, `openai-runner`,
`scripted-runner`, and those #303 and troupe#414 add).

### D3. Merge order: troupe's pull request first

`oob.py` reports both a record with no spec and a spec with no record, so the drift job is red in the gap whichever
merges first. Merging troupe first means this pull request closes the gap, after checking on troupe's `main` that the
spec is gone.

## Risks / Trade-offs

- [#303 or troupe#414's change lands first, editing the same file] → each adds or removes only its own line; a rebase
  is a one-line conflict at most.
- [troupe's change is reworked to keep the spec] → 2.1 checks troupe's `main` before this is marked ready.
