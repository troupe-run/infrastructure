# Design

## Context

See proposal.md for why. The approach is label-troupe-config-specs's (2026-10-23), without its merge-order problem:
the spec is already on troupe's `main`.

- `oob/troupe-spec-purposes.json` maps each troupe spec, by its folder name, to its Purpose as `scripts/oob.py`'s
  `purpose()` reads it: without the `Capability:` line, whitespace collapsed. Its keys are sorted.
- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource. A changed description is an in-place update, and nothing else on the repository changes.
  `scripts/tests/test_labels.py` refuses a description over 100 characters, or one that only repeats the name.
- The `drift (out of band)` job in `tofu.yml` runs `oob.py` beside each plan of `main`, and doesn't wait for the
  apply. `oob.py` also compares each `Capability` option on the troupe roadmap board with its label's declared
  description. The `board descriptions (main)` job sets an option's description only after an approved apply
  (spec: labels). So the record clears the missing-Purpose difference from the merge, but changing a description
  opens a new one until the board is set (D4).

Evidence read on 2026-10-30:

| | |
|---|---|
| `uv run scripts/oob.py` on this branch (09dcebd, = `origin/main`) | one difference: `installation`'s Purpose isn't recorded |
| troupe `main` (e5ede0e) | `openspec/specs/installation/spec.md`, ``Capability: `cap:development`, `cap:user-docs` `` |
| `oob/troupe-spec-purposes.json` | 25 entries, none for `installation` |
| `tofu/labels/troupe.json` | 36 labels |
| troupe specs naming `cap:development` | docs-publishing, flake-hunt, installation, python-support, quality-check, releases |
| troupe specs naming `cap:user-docs` | docs-publishing, installation, user-docs |
| troupe `openspec/config.yaml`, lines 68-71 | every spec names its labels in its Purpose; "A label that doesn't exist yet is added through troupe-run/infrastructure#152 first." Nothing about the Purpose record |

The Purpose, as #224 quotes it:

> How someone outside this repository installs troupe with uv: the bundle package that brings core, its adapters and
> its runners together, the one documented install command, and the check that runs that command on every platform.

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing once this is applied and the board's `development` option has its new description.
- Each label `installation` names has a description checked against its Purpose.
- The next new troupe spec gets its Purpose recorded before its merge turns the drift job red.

**Non-Goals:**
- Re-reading the other eight specs that name these labels. Their Purposes are recorded and `oob.py` reports them as
  unchanged.
- Making the drift job tolerate an unrecorded spec. A red job is how a missed record gets noticed.
- A check in troupe that fails a pull request adding a spec with no record here. That's bigger than a note, and the
  owner chose the note.

## Decisions

### D1. The record is the spec's text, read through `purpose()`

The entry is read from troupe's `main` through `purpose()`, not copied from #224 or this design, so the record is
what the check compares against. It goes between `identity` and `lineage`, keeping the keys sorted.

### D2. The two descriptions

| Label | Description | Length |
|---|---|---|
| `cap:development` | `How troupe itself is built, tested, released and installed: the check, flaky tests, Python versions` | 99 |
| `cap:user-docs` | unchanged: `troupe's user docs, built into troupe.run's /docs: page contract, generated reference, vocabulary` | 99 |

- **cap:development** gains "installed": the bundle package and the check that runs the install command on every
  platform are how troupe is built and tested for someone outside the repository. "releases" leaves the list, which
  "released" already says. The other five specs it covers keep their words: the check (quality-check), flaky tests
  (flake-hunt), Python versions (python-support) and released (releases). docs-publishing wasn't named before
  either, and is also covered by `cap:user-docs`. Owner, 2026-10-30, choosing #224's recommendation.
- **cap:user-docs** already covers the documented install command: it's part of troupe's user docs.

Alternative: keep `cap:development`'s description. Rejected by the owner: an issue about installing troupe should
find its label by what the label says.

### D3. The note goes in troupe's project context, through a troupe issue

troupe's `openspec/config.yaml` is what an agent proposing a troupe spec reads, and already holds the rule about new
labels (#152). A line beside it saying the spec's Purpose is recorded in `oob/troupe-spec-purposes.json`, in an
infrastructure pull request that lands with or before the spec, puts the step where the work happens.

This change can't edit troupe's files. A product repository's files change only through its own pull requests. So
this change raises a troupe issue asking for the line, on the troupe roadmap board, saying it arose from #224, and
names it in the pull request. That troupe issue does the edit.

Alternatives:
- Make the note in `oob/README.md` or `docs/standard-changes.md` more prominent. Rejected by the owner: the note is
  already in `oob/README.md`, and nobody working in troupe reads that file.
- Both. Rejected: the infrastructure note already says it, and a second copy is a second place to keep in step.

### D4. The drift job stays red until the board is set

Found during apply (2026-10-30): with the record and the new description on the branch, `oob.py` reports one
difference, the board's `development` option still holding `cap:development`'s old description, and says "the next
approved apply of main sets it". That's the labels spec working as written. So:

- On the branch, 2.1 expects exactly that one difference, and nothing about Purposes.
- The plan of the pull request and of `main` lists the `development` option's description to set, beside the label's
  in-place update (2.2).
- After the merge, the drift job stays red until the owner approves the apply and `board descriptions (main)` runs.
  That job runs after the oob job in the same run, so the merge's own run is likely still red; the next run, or a
  re-run of the oob job, should pass.

Alternative: keep `cap:development`'s description, so the record alone clears the job from the merge. Rejected: the
owner chose the wider description, and a red window that ends at the apply is how every description change lands.

## Risks / Trade-offs

- [troupe changes `installation`'s Purpose before this merges] → 2.1 re-runs `oob.py` on the branch, rebased onto
  `origin/main`, just before the pull request is opened. If it reports a changed Purpose, the record and D2 are
  updated together.
- [troupe adds another spec before this merges] → 2.1 stops if `oob.py` reports anything else, and the change is
  revised.
- [The troupe issue isn't done before the next spec] → the drift job fails as it did this time, which is the fallback
  either way.

## Migration Plan

The apply updates one description in place, then `board descriptions (main)` sets the `development` option's.
Rolling back is a revert of the pull request: the old description
returns, and the record goes with it, so the drift job fails again until `installation`'s Purpose is recorded.
