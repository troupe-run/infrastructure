# Design

## Context

See proposal.md for why. The approach is effects-spec-purpose's (2026-11-04), with one spec and one description.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it: without the `Capability:` line, whitespace collapsed. Its keys are sorted.
- `stale_descriptions()` reports a spec whose Purpose isn't recorded, one whose Purpose has changed, **and a record
  with no spec**, so a record that lands before its spec turns the drift job red too.
- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource, so a changed description is an in-place update. `scripts/tests/test_labels.py` refuses a description over
  100 characters, or one that only repeats the name.
- `oob.py` also compares each `Capability` option on the troupe roadmap board with its label's declared description.
  `board descriptions (main)` sets them only after an approved apply (spec: labels).

Evidence read on 2026-11-04:

| | |
|---|---|
| troupe#287 (`runtimes`, head 68c084f) | draft. Adds `specs/runtimes`; its other deltas (config, config-files, runner-protocol, runs, scripted-runner) have no Purpose section |
| `purpose()` of `runtimes` on 68c084f | exactly #272's quote |
| `runtimes`'s Capability line | `` `cap:config`, `cap:actor-runners` `` |
| troupe specs on `main` (dc5a704) naming `cap:config` or `cap:actor-runners` | actor-runners, claude-code-runner, config, config-files, effects, runner-protocol, runner-tools, scripted-runner |
| `oob/troupe-spec-purposes.json` | 30 entries, no `runtimes` |
| `tofu/labels/troupe.json` | 36 labels |

The Purpose:

> **runtimes**: Names the services runners talk to, once, in config: each runtime's endpoint, default model and
> credential, resolved from troupe's defaults, the theatre's config and the person's environment with the source of
> each value, and the credential held only by reference and kept out of everything troupe writes.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once troupe#287 and this have merged, the apply has run, and the
  board's `config` option has its new description.
- Each label the new spec names has a description checked against its Purpose.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec, or a record that comes before its spec. A red job is how a missed
  or early record gets noticed.
- Re-reading the Purposes of the other specs that name `cap:config` or `cap:actor-runners`. They're recorded, and
  `oob.py` reports them as unchanged. The new `cap:config` wording is checked against them in D2 only so it doesn't
  stop describing them.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read through `purpose()`, not copied from #272 or this design, so the record is what the check compares
against. Until troupe#287 merges, the source is its branch
(`openspec/changes/runtimes/specs/runtimes/spec.md` at `ref=runtimes`). Once it merges, 2.1 re-reads it from troupe's
`main` (`openspec/specs/runtimes/spec.md`), and updates the record and D2 if review changed it. `runtimes` goes
between `runs` and `scripted-runner`, keeping the keys sorted.

### D2. The descriptions

| Label | Description | Length |
|---|---|---|
| `cap:config` | `A theatre's config as events with lineage, merged across branches, and its kinds: actors, runtimes` | 98 |
| `cap:actor-runners` | unchanged: `Running an actor through a runner: launch, limits, cancel, its tool calls, and one trusted outcome` | 99 |

The owner chose `cap:config`'s wording on 2026-11-04, over keeping it and over an open-ended "actors, runtimes and
more kinds".

- **cap:config** said "and the actor, its first kind". `runtimes` is config's second kind: it names each runtime's
  endpoint, default model and credential, resolved across troupe's defaults, the theatre's config and the person's
  environment. "its kinds: actors, runtimes" names both, and keeps the first half, which `config` and `config-files`
  are about. `effects` stays covered: an actor's effects are part of the actor.
- **cap:actor-runners** already covers the spec's runner part: the services a runner talks to are part of running an
  actor through it.

Alternatives:
- Keep the old wording. Rejected by the owner: still true, but a reader looking for where runtimes are configured
  wouldn't find them under it.
- "…: actors, runtimes and more kinds". Rejected by the owner: it describes kinds that don't exist yet.

### D3. Merge order: troupe#287 first

As in effects-spec-purpose (D3): `oob.py` reports both an unrecorded spec and a record with no spec, so the drift job
is red in the gap whichever merges first. Merging troupe first means the gap is closed by this pull request, which
re-reads the Purpose from `main` before it's marked ready. The board's `config` option is then red until the apply
and `board descriptions (main)` have run.

## Risks / Trade-offs

- [Review changes the Purpose in troupe#287, or renames the spec] → 2.1 re-reads it from `main` before this is marked
  ready, and D2 is checked against the new text.
- [troupe#287 merges after other troupe changes that add specs] → each needs its own record; 2.2's `oob.py` run shows
  any that this change doesn't cover, and the change stops rather than recording them.
