# Design

## Context

See proposal.md for why. The approach is sdk-spec-purposes's (2026-11-03), with one spec and one description.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it: without the `Capability:` line, whitespace collapsed. Its keys are sorted.
- `stale_descriptions()` reports a spec whose Purpose isn't recorded, one whose Purpose has changed, **and a record
  with no spec**, so a record that lands before its spec turns the drift job red too.
- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource, so a changed description is an in-place update. `scripts/tests/test_labels.py` refuses a description over
  100 characters, or one that only repeats the name.
- `oob.py` also compares each `Capability` option on the troupe roadmap board with its label's declared description.
  `board descriptions (main)` sets them only after an approved apply (spec: labels).

Evidence read on 2026-11-03:

| | |
|---|---|
| troupe#273 (`declared-effects`, head ca8431c) | draft. Adds `specs/effects`; its other deltas (config, runner-protocol, runner-tools, plugin-sdk, actor-runners, runs, claude-code-runner, scripted-runner, stages) change no Purpose |
| `purpose()` of `effects` on ca8431c | exactly #264's quote |
| `effects`'s Capability line | `` `cap:effects`, `cap:config` `` |
| troupe specs on `main` (afd3bc8) naming `cap:effects` | none |
| troupe specs on `main` naming `cap:config` | config, config-files |
| `oob/troupe-spec-purposes.json` | 29 entries, no `effects` |
| `tofu/labels/troupe.json` | 36 labels |

The Purpose:

> **effects**: What an actor may change, declared in its config, and what troupe does with the declaration: how it's
> written, the read-only default, how the files a run must change sit inside it, how a run's changes are audited
> against it after the run, and the scratch space every run gets outside it. None of it is enforcement, which only a
> stage can give.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once troupe#273 and this have merged, the apply has run, and the
  board's `effects` option has its new description.
- Each label the new spec names has a description checked against its Purpose.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec, or a record that comes before its spec. A red job is how a missed
  or early record gets noticed.
- Re-reading the Purposes of the other specs that name `cap:config`. They're recorded, and `oob.py` reports them as
  unchanged.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read through `purpose()`, not copied from #264 or this design, so the record is what the check compares
against. Until troupe#273 merges, the source is its branch
(`openspec/changes/declared-effects/specs/effects/spec.md` at `ref=declared-effects`). Once it merges, 2.1 re-reads it
from troupe's `main` (`openspec/specs/effects/spec.md`), and updates the record and D2 if review changed it. `effects`
goes between `docs-publishing` and `event-store`, keeping the keys sorted.

### D2. The descriptions

| Label | Description | Length |
|---|---|---|
| `cap:effects` | `What an actor may touch, declared in config, applied by its runner, audited, and enforced by a stage` | 100 |
| `cap:config` | unchanged: `A theatre's config as events with lineage, merged across branches, and the actor, its first kind` | 97 |

#264's wording, for the owner to confirm.

- **cap:effects** had said the declaration is "enforced by its stage", which only #65's stage will do. The `effects`
  spec covers what comes before it: the runner applies the declaration, troupe audits each run's changes against it,
  and none of that is enforcement. "applied by its runner, audited" says the first two; "enforced by a stage" keeps
  the label's place for #65. "(files, network)" goes to stay within 100 characters: "touch" still covers both, and
  network effects aren't declared yet.
- **cap:config** already covers the spec's config part: an actor's effects are part of the actor, its first kind.

Alternatives:
- Keep the old wording. Rejected: a reader of the label would take "enforced" to describe what `effects` does today,
  which the spec says it doesn't.
- "What an actor may change, …". Rejected: "touch" leaves room for network effects, which the label is also for.

### D3. Merge order: troupe#273 first

As in sdk-spec-purposes (D3): `oob.py` reports both an unrecorded spec and a record with no spec, so the drift job is
red in the gap whichever merges first. Merging troupe first means the gap is closed by this pull request, which
re-reads the Purpose from `main` before it's marked ready. The board's `effects` option is then red until the apply
and `board descriptions (main)` have run, as sdk-spec-purposes' D4 describes.

## Risks / Trade-offs

- [Review changes the Purpose in troupe#273] → 2.1 re-reads it from `main` before this is marked ready, and D2 is
  checked against the new text.
- [The owner prefers other wording for `cap:effects`] → It's one line in `tofu/labels/troupe.json` and in D2; the
  plan shows exactly what changes before anything is applied.
