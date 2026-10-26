# Proposal

Issue: #158, the first of #151's two applies.

## Why

troupe-run/troupe#169 decided that troupe's issues are labelled by capability, not by spec (owner, 2026-10-26). Each
spec now names its capability labels in a `Capability:` line under its Purpose. troupe-run/troupe#171 (f159b5b) added
those lines to all 25 specs on troupe's `main`. `scripts/oob.py` still requires a `cap:<folder>` label for every spec
folder, and it can't read the new line. It also compares each spec's whole Purpose, which now includes that line.
`uv run scripts/oob.py` on `main` (801fbee) reports 25 differences of this form, one per spec:

```
troupe labels: 'cap:cli' spec's Purpose has changed; review its description in tofu/labels/troupe.json and update oob/troupe-spec-purposes.json
```

Five specs (`flake-hunt`, `python-support`, `quality-check`, `releases`, `docs-publishing`) name `cap:development`,
which isn't declared yet. The relabelling in #151 can't start until that label exists on GitHub, so it needs an apply
of its own first.

## What Changes

- **The `troupe specs` check reads the labels each spec names.** It reads them from the first non-blank line of the
  spec's `## Purpose`. It reports a spec that names no label, a line that isn't in the agreed shape, and a label that
  isn't declared in `tofu/labels/troupe.json`, naming the spec each time. It no longer requires a `cap:<folder>` label
  per folder (design D1, D2). A declared label that no spec names is still not reported.
- **The Purpose record is keyed by spec, not by label.** `oob/troupe-spec-purposes.json` maps each spec folder to its
  Purpose without the `Capability:` line. A changed Purpose is reported naming the spec and every label it names,
  whose descriptions then need a review (design D3). The 25 recorded Purposes are unchanged apart from their keys:
  each one matches troupe's `main` once the line is left out.
- **`cap:development` is added**, colour `1D76DB`, described from troupe#169 (design D4).
- **`cap:flows` gets a real description** in place of `TBD`, from the milestones that build it (design D4).
- **No label is removed or renamed.** The 12 folded labels and `cap:lifecycle` stay declared, and every issue keeps
  its labels.

Out of scope, and left on #151 for its second change:
- Relabelling troupe's issues from the folded labels to the labels their specs now name.
- Removing the 12 folded labels and `cap:lifecycle` (48 → 36 labels).

Also out of scope:
- The `App installations: 'troupe-run-review'` difference, which #154 tracks.
- A guard check at proposal time (#153), and adding a new label as a standard change (#152).
- Any change to troupe-run/troupe's files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `labels`: the check that a troupe spec has a label reads the labels the spec names, not its folder name. The
  Purpose record is kept per spec, and a changed Purpose names the labels whose descriptions need a review. A
  capability label's description now covers every spec that names it.

## Impact

- `scripts/oob.py`: `unlabelled_specs` and `stale_descriptions` are rewritten around a parser for the `Capability:`
  line. Every spec's `spec.md` is now read, once, for both checks.
- `scripts/tests/test_oob.py`: the troupe spec and Purpose tests are rewritten for the new shape.
- `oob/troupe-spec-purposes.json`: re-keyed from `cap:<name>` to `<name>` (25 entries, same text).
- `oob/README.md`: the two rows and the paragraph on a new capability's label.
- `tofu/labels/troupe.json`: `cap:development` added (48 → 49), and `cap:flows` re-described.
- `openspec/specs/labels/spec.md`, through the delta.
- GitHub, after the owner approves the plan: `cap:development` is created on troupe-run/troupe, and `cap:flows`'
  description changes. Nothing else changes.
- The drift job's 25 `troupe labels` differences clear once this is merged. The `troupe-run-review` one stays until
  #154 lands.
- #158 is closed by this change's pull request. #151 stays open for the relabelling.
