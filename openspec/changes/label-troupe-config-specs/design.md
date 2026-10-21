# Design

## Context

See proposal.md for why. The approach is label-troupe-docs-specs's (2026-10-20), with one difference: the specs
aren't on troupe's `main` yet.

- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource. A new name is a label created on the next apply, a changed description is an in-place update, and
  nothing else on the repository changes.
- `oob/troupe-spec-purposes.json` maps each `cap:<name>` with a troupe spec to that spec's Purpose as
  `scripts/oob.py`'s `purpose()` reads it. `oob.py` reports a changed Purpose, a labelled spec with nothing recorded,
  and a record with no spec. Both files are sorted by label name.
- `scripts/tests/test_labels.py` refuses a description over 100 characters, or one that only repeats the name.
- troupe's archive copies a delta spec's `## Purpose` into the new main spec unchanged (seen for `docs-publishing`:
  the archived delta and `openspec/specs/docs-publishing/spec.md` carry the same text). So the Purposes on the
  `config-model` branch are what `oob.py` will read from `main`, unless the branch changes them first.

Evidence read on 2026-10-21:

| | |
|---|---|
| `uv run scripts/oob.py` on `main` (d202155) | no differences |
| `tofu/labels/troupe.json` | 45 labels; `cap:config` is "Config files under .troupe/: layout, per-file schemas, the hand-edit sweep and write-back" |
| `oob/troupe-spec-purposes.json` | 21 entries, none for `cap:config` |
| troupe `config-model` branch (2f21080, with uncommitted work in progress) | new specs `config` and `config-files`; modifies `cli`, `client-protocol`, `event-store`, `runner-protocol`, `runs` and `scripted-runner`, all labelled and recorded |
| troupe issues with `cap:config` | 16, listed under D3 |

The two Purposes on the `config-model` branch, as `purpose()` reads them:

- **config:** "Holds a theatre's config as events with lineage, works out the config every command uses from them,
  including across merged branches, and defines the actor, the first kind of config."
- **config-files:** "Projects a theatre's config to files under `.troupe/` that a person can read and review as
  diffs, never losing a file a person wrote, and keeps the theatre's own git files holding what troupe needs."

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing for troupe's labels once troupe#60 and this are both merged and applied.
- Each of the two specs has a label whose description was checked against its Purpose.

**Non-Goals:**
- Re-reading the six modified specs' Purposes. troupe#60's deltas add and modify requirements only; if one rewrites a
  Purpose, `oob.py` reports it after #60 merges and 3.1 catches it.
- Making the drift job tolerate a spec until its label lands. A red job is how a missing label gets noticed.

## Decisions

### D1. The two descriptions

| Label | Description | Length |
|---|---|---|
| `cap:config` | `A theatre's config as events with lineage, merged across branches, and the actor, its first kind` | 96 |
| `cap:config-files` | `Config projected to files under .troupe/ for review as diffs, never losing a file a person wrote` | 96 |

- **config** keeps the Purpose's three parts: events with lineage, the merge across branches, and the actor.
  "Works out the config every command uses" goes, since it's what holding config means.
- **config-files** keeps the projection, the diffs and the promise never to lose a person's file. "The theatre's own
  git files" goes, because 100 characters can't hold it, and an issue about config files is far more likely to be
  about the projection.

`.troupe/` is written without backticks, as label-troupe-docs-specs D1 wrote `/docs`: GitHub shows a label
description as plain text.

Alternative: keep `cap:config`'s description and only add `cap:config-files`, as #116 asks. Rejected: recording
`config`'s Purpose is required once the spec exists ("A description written from a spec records that spec's
Purpose"), and recording it beside a description about files would record a check that was never made.

### D2. The record is the spec's text, verbatim

As in label-troupe-docs-specs D2: each recorded Purpose is read through `purpose()`, not copied from this design.
Until #60 merges, the source is the `config-model` branch's delta
(`openspec/changes/config-model/specs/<name>/spec.md`). Once it merges, 3.1 re-reads both from troupe's `main`
(`gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md`) and updates the record and D1 if either
changed. `cap:config-files` goes after `cap:config` in `tofu/labels/troupe.json`. Both entries go after
`cap:client-protocol` in the record, `cap:config` first.

### D3. Labelling troupe's config-file issues

After the apply, once the label exists, add `cap:config-files` to the issues about config's files. None loses
`cap:config`: each is also about config itself.

| Issue | Why |
|---|---|
| troupe#60 "Config model: actors set with troupe config set, projected to files under .troupe/" | the issue both specs come from |
| troupe#6 "Config layout: convention over configuration" (closed) | the file layout, which config-files projects to |
| troupe#5 "Hand-edit granularity, and whether the house watches files" (closed) | hand edits to the files |
| troupe#119 "Placeholder: the hand-edit sweep, reading hand edits back into config events" | reads the files back |
| troupe#138 "Placeholder: renaming config entities with troupe config mv, and detecting hand moves" | hand moves are moved files |

The other 11 `cap:config` issues (#2, #7, #8, #38, #44, #45, #61, #67, #71, #135, #136) are about config's model,
history, policy or plugins, not its files, and are left as they are.

### D4. Merge order: troupe#60 first

If this merged first, the apply would describe `cap:config` by specs that don't exist yet, and the drift job would
report both recorded Purposes as having no spec on every run until #60 merged. Merging #60 first leaves one window,
from #60's merge to this apply, where the job reports `config-files` unlabelled and `cap:config` unrecorded. That's
the usual order for a new spec, and the shorter window.

Alternative: wait to open this change until #60 merges. Rejected by the owner (2026-10-21): the work can run in
parallel, and the owner orders the merges.

## Risks / Trade-offs

- [troupe#60 changes a Purpose before it merges] → 3.1 re-reads both from troupe's `main` after the merge and
  updates the record and the description together.
- [#60 renames or drops a spec] → 3.1 stops and the change is revised before its pull request is merged.
- [troupe adds another spec before this merges] → 3.1 re-runs `oob.py` on the branch and stops if it reports
  anything more.

## Migration Plan

The apply creates one label and updates one description. Rolling back is a revert of the pull request: the label is
deleted (nothing carries it until D3) and `cap:config`'s old description returns.
