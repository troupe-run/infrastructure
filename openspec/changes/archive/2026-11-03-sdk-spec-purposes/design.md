# Design

## Context

See proposal.md for why. The approach is installation-spec-purpose's (2026-10-30), with two specs and two
descriptions, and label-troupe-config-specs's merge order (2026-10-23, D4), since the specs aren't on troupe's `main`
yet.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it: without the `Capability:` line, whitespace collapsed. Its keys are sorted.
- `stale_descriptions()` reports a spec whose Purpose isn't recorded, one whose Purpose has changed, **and a record
  with no spec**. So a record that lands before its spec turns the drift job red too.
- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource. A changed description is an in-place update. `scripts/tests/test_labels.py` refuses a description over
  100 characters, or one that only repeats the name.
- `oob.py` also compares each `Capability` option on the troupe roadmap board with its label's declared description.
  `board descriptions (main)` sets them only after an approved apply (spec: labels).

Evidence read on 2026-11-02:

| | |
|---|---|
| `uv run scripts/oob.py` on this branch (359ee07, = `origin/main`) | one difference: the App's `pull_requests: read`, which #261 declares. Nothing about troupe's specs |
| troupe#268 (`runner-sdk`, head 581dc2f) | draft, blocked. Adds `specs/plugin-sdk` and `specs/runner-tools`; its `installation`, `quality-check` and `scripted-runner` deltas change no Purpose |
| troupe `main` (5837ccc) | neither spec |
| `purpose()` of each new spec | exactly #262's quotes on 581dc2f (proposal), on 454da7a (task 1.1, after the head moved), on 51041e0, and on troupe `main` at e4a33c2, troupe#268's merge (task 2.1) |
| `plugin-sdk`'s Capability line | `` `cap:plugins`, `cap:protocol` `` |
| `runner-tools`'s Capability line | `` `cap:actor-runners`, `cap:plugins` `` |
| troupe specs on `main` naming `cap:actor-runners` | actor-runners, claude-code-runner, runner-protocol, scripted-runner |
| troupe specs on `main` naming `cap:plugins` | none |
| troupe specs on `main` naming `cap:protocol` | client-protocol, protocol, runner-protocol |
| `oob/troupe-spec-purposes.json` | 27 entries, neither spec |
| `tofu/labels/troupe.json` | 36 labels |

The Purposes:

> **plugin-sdk**: The plugin SDK: one small, framework-free package with the public API that plugins build against,
> starting with the runner contract's types and running a model's tool calls. Core takes the contract's types from it
> too, so they have one definition, and plugins depend on it instead of on core.

> **runner-tools**: How troupe's own runners carry out a model's tool calls in the workspace: which tools there are,
> how each call is checked against the actor's declared effects and kept inside the workspace, and how calls and
> results are reported to the model and recorded as run events.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing about troupe's specs once troupe#268 and this have merged, the apply has run, and the
  board's two options have their new descriptions.
- Each label the two specs name has a description checked against their Purposes.

**Non-Goals:**
- Making the drift job tolerate an unrecorded spec, or a record that comes before its spec. A red job is how a
  missed or early record gets noticed.
- Re-reading the Purposes of the other specs that name these labels. They're recorded, and `oob.py` reports them as
  unchanged.
- Changing how troupe asks for the record. troupe#199's line worked: #262 was raised before troupe's merge.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

Each entry is read through `purpose()`, not copied from #262 or this design, so the record is what the check compares
against. Until troupe#268 merges, the source is its branch
(`openspec/changes/runner-sdk/specs/<name>/spec.md` at `ref=runner-sdk`). Once it merges, 2.1 re-reads both from
troupe's `main` (`openspec/specs/<name>/spec.md`) and updates the record and D2 if either changed in review.
`plugin-sdk` goes between `platform` and `policy`, and `runner-tools` between `runner-protocol` and `runs`, keeping
the keys sorted.

### D2. The descriptions

| Label | Description | Length |
|---|---|---|
| `cap:plugins` | `Ports, transports, the plugin SDK, and how plugins are declared, acquired and trusted` | 85 |
| `cap:actor-runners` | `Running an actor through a runner: launch, limits, cancel, its tool calls, and one trusted outcome` | 98 |
| `cap:protocol` | unchanged: `Strict, language-neutral JSON Schema contracts in protocol/ and each plugin, for every surface` | 94 |

Owner, 2026-11-02, choosing #262's wording.

- **cap:plugins** gains "the plugin SDK", which `plugin-sdk` is about and `runner-tools` builds on. "(direct or
  JSON-RPC)" goes to make room: "transports" still covers it. No spec on `main` names the label, so nothing else
  constrains it.
- **cap:actor-runners** gains "its tool calls", which is `runner-tools`. "process" goes to stay within 100
  characters: "runner" is still the out-of-process runner `actor-runners` describes. Launch, limits, cancel and one
  trusted outcome keep `actor-runners`'s words. `claude-code-runner`, `runner-protocol` and `scripted-runner` are
  runners, so "running an actor through a runner" still covers them.
- **cap:protocol** already covers `plugin-sdk`'s part: the contract's types it holds are checked against those JSON
  Schema contracts.

Alternative: keep "runner process" and drop another word from `cap:actor-runners` (102 characters as is). Rejected
by the owner: #262's wording reads better and fits.

### D3. Merge order: troupe#268 first

`stale_descriptions()` reports a record with no spec as well as a spec with no record, so neither order avoids a red
drift job, and the two repositories can't merge at once. Merging troupe#268 first is the order label-troupe-config-
specs chose (owner, 2026-10-21) and the one #224 and #228 ended up in:

- Its window runs from troupe#268's merge until this merges, and reports two unrecorded Purposes: the usual sign of a
  new spec.
- The record and the descriptions are then checked against troupe's `main`, not a branch that review may still
  change.
- Merging this first would report both records as having no spec until troupe#268 merges, and describe the labels by
  specs that don't exist yet. #262's "with or before" didn't account for that check.

troupe#268 is still a draft (owner, 2026-11-02: it runs in parallel). This change is built and reviewed meanwhile,
and its pull request is marked ready only after 2.1 has re-read the Purposes from `main`.

### D4. The drift job stays red until the board is set

As in installation-spec-purpose D4: with the record and the new descriptions merged, `oob.py` reports the board's
`plugins` and `actor-runners` options still holding the old descriptions until the owner approves the apply and
`board descriptions (main)` runs. On the branch, 2.2 expects exactly those two differences, and nothing about
Purposes. The pull request's plan shows only the two labels' in-place updates. Only `plan (main)` plans the board's
descriptions.

## Risks / Trade-offs

- [Review changes a Purpose before troupe#268 merges] → 2.1 re-reads both from `main` after the merge. If either
  changed, the record and D2 are updated together and 1.1–1.2's checks re-run.
- [troupe#268 renames or drops a spec, or names other labels] → 2.1 stops and the change is revised.
- [troupe adds another spec before this merges] → 2.2 stops if `oob.py` reports anything else.
- [#261 hasn't merged when 2.2 runs] → `oob.py` also reports the App's `pull_requests: read`. That difference is #261's,
  and 2.2 names it rather than counting it as this change's.

## Migration Plan

The apply updates two descriptions in place, then `board descriptions (main)` sets the two options'. Rolling back is a
revert of the pull request: the old descriptions return, and the records go with them, so the drift job fails again
until both Purposes are recorded.
