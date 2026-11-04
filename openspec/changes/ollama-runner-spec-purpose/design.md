# Design

## Context

See proposal.md for why. The approach is effects-spec-purpose's (2026-11-04), with one spec and no description to
change.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it: without the `Capability:` line, whitespace collapsed. Its keys are sorted.
- `stale_descriptions()` reports a spec whose Purpose isn't recorded, one whose Purpose has changed, **and a record
  with no spec**, so a record that lands before its spec turns the drift job red too.

Evidence read on 2026-11-04:

| | |
|---|---|
| troupe#283 (`local-model-runner`, head 0974956) | ready, CI passed on every platform. Adds `specs/ollama-runner`; its other deltas (runner-protocol, runs, cli, config, quality-check) change no Purpose |
| `purpose()` of `ollama-runner` on 0974956 | exactly #266's quote |
| `ollama-runner`'s Capability line | `` `cap:actor-runners` `` |
| `oob/troupe-spec-purposes.json` | 30 entries, no `ollama-runner` |
| `tofu/labels/troupe.json` | 36 labels |

The Purpose:

> **ollama-runner**: An actor runner for a model served by Ollama: it drives Ollama's own chat API with troupe's own
> tool loop, checking each tool call against the actor's declared effects, and reports the run through the runner
> contract, with no credential, no cost per run and no network beyond the endpoint.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once troupe#283 and this have merged.
- The label the new spec names has a description checked against its Purpose.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec, or a record that comes before its spec. A red job is how a missed
  or early record gets noticed.
- Re-reading the Purposes of the other specs that name `cap:actor-runners`. They're recorded, and `oob.py` reports
  them as unchanged.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read through `purpose()`, not copied from #266 or this design, so the record is what the check compares
against. Until troupe#283 merges, the source is its branch
(`openspec/changes/local-model-runner/specs/ollama-runner/spec.md` at `ref=local-model-runner`). Once it merges, 2.1
re-reads it from troupe's `main` (`openspec/specs/ollama-runner/spec.md`), and updates the record and D2 if review
changed it. `ollama-runner` goes between `lineage` and `platform`, keeping the keys sorted.

### D2. The description: `cap:actor-runners` is kept

| Label | Description | Length |
|---|---|---|
| `cap:actor-runners` | unchanged: `Running an actor through a runner: launch, limits, cancel, its tool calls, and one trusted outcome` | 97 |

The spec is one more runner, and the label already covers what it adds: running an actor through a runner, its
limits, cancelling it, and its tool calls, which this runner carries out itself. Nothing in its Purpose falls outside
the description, as `claude-code-runner`'s and `scripted-runner`'s don't.

Alternative: name local models or Ollama in the description. Rejected: a label covers every runner, and naming one
engine would make the others look out of scope.

### D3. Merge order: troupe#283 first

As in effects-spec-purpose (D3): `oob.py` reports both an unrecorded spec and a record with no spec, so the drift job
is red in the gap whichever merges first. Merging troupe first means the gap is closed by this pull request, which
re-reads the Purpose from `main` before it's marked ready.

## Risks / Trade-offs

- [Review changes the Purpose in troupe#283] → 2.1 re-reads it from `main` before this is marked ready, and D2 is
  checked against the new text.
