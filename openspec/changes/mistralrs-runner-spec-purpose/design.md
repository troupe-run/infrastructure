# Design

## Context

See proposal.md for why. The approach is lm-studio-runner-spec-purpose's (2026-11-12): one spec, and no description
to change.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it: without the `Capability:` line, whitespace collapsed. Its keys are sorted.
- `stale_descriptions()` reports a spec whose Purpose isn't recorded, one whose Purpose has changed, **and a record
  with no spec**, so a record that lands before its spec turns the drift job red too.

Evidence read on 2026-11-14:

| | |
|---|---|
| troupe's `in-process-runner` change | proposed on branch `in-process-runner` (troupe#422). Adds `specs/mistralrs-runner`; its other deltas (runtimes, runner-protocol, cli) change no Purpose |
| `purpose()` of `mistralrs-runner` on its branch | exactly #307's quote |
| `mistralrs-runner`'s Capability line | `` `cap:actor-runners` `` |
| `oob/troupe-spec-purposes.json` | 34 entries, no `mistralrs-runner` |

The Purpose:

> **mistralrs-runner**: An actor runner for a model loaded inside its own process by mistral.rs: it drives the
> model with troupe's own tool loop, checking each tool call against the actor's declared effects, and reports the
> run through the runner contract, with no server, no credential, no cost per run and no network.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once troupe's `in-process-runner` change and this have merged.
- The label the new spec names has a description checked against its Purpose.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec, or a record that comes before its spec.
- Any other entry, including `lm-studio-runner`'s, which troupe#413's own change removes, and
  `mistralrs-runner`'s, which #307 adds.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read through `purpose()`, not copied from #307 or this design, so the record is what the check compares
against. Until troupe's change merges, the source is its branch
(`openspec/changes/in-process-runner/specs/mistralrs-runner/spec.md` at `ref=in-process-runner`). Once it merges, 2.1
re-reads it from troupe's `main` (`openspec/specs/mistralrs-runner/spec.md`), and updates the record and D2 if review
changed it. `mistralrs-runner` goes between `lm-studio-runner` and `ollama-runner`, keeping the keys sorted.

### D2. The description: `cap:actor-runners` is kept

| Label | Description | Length |
|---|---|---|
| `cap:actor-runners` | unchanged: `Running an actor through a runner: launch, limits, cancel, its tool calls, and one trusted outcome` | 97 |

The spec is one more runner, and the label already covers what it adds: running an actor through a runner, its
limits, cancelling it, and its tool calls, which troupe carries out with a model loaded in the runner's own process.

### D3. Merge order: troupe's pull request first

As in lm-studio-runner-spec-purpose (D3): `oob.py` reports both an unrecorded spec and a record with no spec, so the
drift job is red in the gap whichever merges first. Merging troupe first means this pull request closes the gap, after
re-reading the Purpose from `main` before it's marked ready.

## Risks / Trade-offs

- [Review changes the Purpose in troupe's change] → 2.1 re-reads it from `main` before this is marked ready, and D2 is
  checked against the new text.
- [troupe#413 and #415 edit the same file] → each adds or removes only its own line; a rebase onto whichever lands
  first is a one-line conflict at most.
