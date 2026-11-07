# Design

## Context

See proposal.md for why. The approach is ollama-runner-spec-purpose's (2026-11-04): one spec, and no description to
change.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it: without the `Capability:` line, whitespace collapsed. Its keys are sorted.
- `stale_descriptions()` reports a spec whose Purpose isn't recorded, one whose Purpose has changed, **and a record
  with no spec**, so a record that lands before its spec turns the drift job red too.

Evidence read on 2026-11-06:

| | |
|---|---|
| troupe#297 (`openai-style-runner`) | a draft, CI not yet run. Adds `specs/openai-runner`; its other deltas (runs, config, cli) change no Purpose |
| `purpose()` of `openai-runner` on its branch | exactly #276's quote |
| `openai-runner`'s Capability line | `` `cap:actor-runners` `` |
| `oob/troupe-spec-purposes.json` | 32 entries, no `openai-runner` |
| `tofu/labels/troupe.json` | 36 labels |

The Purpose:

> **openai-runner**: The OpenAI runner: an actor runner that drives OpenAI's Responses API, or any service that serves
> it, with troupe's own tool loop, so the runner contract is tested by a hosted engine that needs a credential, costs
> money and fails in a hosted service's ways.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once troupe#297 and this have merged.
- The label the new spec names has a description checked against its Purpose.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec, or a record that comes before its spec. A red job is how a missed
  or early record gets noticed.
- Re-reading the Purposes of the other specs that name `cap:actor-runners`. They're recorded, and `oob.py` reports
  them as unchanged.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read through `purpose()`, not copied from #276 or this design, so the record is what the check compares
against. Until troupe#297 merges, the source is its branch
(`openspec/changes/openai-style-runner/specs/openai-runner/spec.md` at `ref=openai-style-runner`). Once it merges, 2.1
re-reads it from troupe's `main` (`openspec/specs/openai-runner/spec.md`), and updates the record and D2 if review
changed it. `openai-runner` goes between `ollama-runner` and `platform`, keeping the keys sorted.

### D2. The description: `cap:actor-runners` is kept

| Label | Description | Length |
|---|---|---|
| `cap:actor-runners` | unchanged: `Running an actor through a runner: launch, limits, cancel, its tool calls, and one trusted outcome` | 97 |

The spec is one more runner, and the label already covers what it adds: running an actor through a runner, its
limits, cancelling it, and its tool calls, which this runner carries out itself. Its credential comes from a runtime,
which `runtimes`' own record and `cap:config` cover.

Alternative: name hosted services or credentials in the description. Rejected: a label covers every runner, and
naming one kind would make the others look out of scope.

### D3. Merge order: troupe#297 first

As in ollama-runner-spec-purpose (D3): `oob.py` reports both an unrecorded spec and a record with no spec, so the drift
job is red in the gap whichever merges first. Merging troupe first means the gap is closed by this pull request, which
re-reads the Purpose from `main` before it's marked ready.

## Risks / Trade-offs

- [Review changes the Purpose in troupe#297] → 2.1 re-reads it from `main` before this is marked ready, and D2 is
  checked against the new text.
