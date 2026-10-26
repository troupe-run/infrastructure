# Proposal

Issue: #153, the last part of #150.

## Why

A troupe spec names its capability labels in a `Capability:` line, the first non-blank line of its Purpose
(troupe-run/troupe#169, #170). Today a label it names that isn't declared in `tofu/labels/troupe.json` is found only
by the drift check, `scripts/oob.py`, which reads troupe's `main`. So it shows only after the spec archives, as a red
`drift (out of band)` job on infrastructure's `main` (#132). By then the work that needed the label is merged, and the
label's pull request comes after it.

The label is known the moment a change proposes the spec, or edits the line of one that exists. #152 made adding a
label a standard change (`docs/standard-changes.md`, "A capability label", #164). This change has the guard find a
missing label on the push that names it, and point at that standard change, so the label's pull request can merge
first.

## What Changes

- **A new guard rule, `capability-label`, on the `guard` GitHub check, in troupe-run/troupe only.** For each spec in
  the range's scope it reads the `Capability:` line, and fails when the line is missing, malformed, or names a label
  that `tofu/labels/troupe.json` on infrastructure's `main` doesn't declare. Each failure names the spec (and the
  change, for a proposed spec), the label, and the fix: add the label as the standard change, linked by its anchor in
  `docs/standard-changes.md`, or name a label that exists (design D1, D5).
- **What it judges** (design D2):
  - a main spec the range changes, which is how a spec's labels change once it exists, since OpenSpec ignores a
    delta's Purpose for an existing spec (troupe#170 design D1);
  - a delta spec in an active change the range changes, when its spec doesn't exist yet: that delta's Purpose becomes
    the new spec's (troupe#170 design D3).
  - On a push to `main`, and when the range changes the guard itself, every main spec and every such delta, as for
    `openspec-strict`.
- **The labels are read from GitHub when the check runs** (design D3): `tofu/labels/troupe.json` at infrastructure's
  `main`, through the contents API with the run's token. A read that fails, or a file that isn't a list of labels,
  fails the rule; it never passes. Nothing is fetched when the scope is empty.
- **Only on GitHub, not in the local hooks** (design D4). The guard's local hooks work offline, and this rule needs
  another repository's file. The `guard` check runs on every push to every branch, so the failure comes on the push
  that names the label. It isn't overridable, like `openspec-strict`.
- **One parser for the line** (design D6). The `Capability:` line's reading moves from `scripts/oob.py` into
  `scripts/guard.py`, which is delivered, and `oob.py` imports it. The drift check's behaviour doesn't change.
- `.github/workflows/guard.yml` passes the run's token to the guard step. `docs/development-workflow.md` gets the
  rule's row.

Out of scope:
- A delta for an existing spec whose Purpose carries a different `Capability:` line. OpenSpec ignores that Purpose,
  so the guard doesn't read it either (design, Non-Goals).
- Checking that a troupe issue carries the labels its spec names, or the board's Capability options (`oob.py` does
  that, #151).
- Making the label: that's the standard change. The guard only points at it.
- Any repository but troupe: infrastructure's and the website's specs have no `Capability:` line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: the `guard` check fails under `capability-label` when a troupe spec in its scope names no
  label, a malformed line, or a label infrastructure doesn't declare on `main`; and fails, rather than passes, when it
  can't read the declared labels.

## Impact

- `scripts/guard.py`: the `capability-label` rule, the line's parser (moved from `oob.py`), the labels read, and its
  call from `run_ci_entry`, after `openspec-strict`.
- `scripts/oob.py`: imports the parser from `guard.py`; no change in what it reports.
- `.github/workflows/guard.yml`: `GITHUB_TOKEN` on the guard step.
- `scripts/tests/`: tests for the rule, with the labels read and the repository injected; `test_oob.py` keeps passing
  unchanged.
- `docs/development-workflow.md`: the layer table and the rule's row.
- `openspec/specs/development-workflow/spec.md`, through the delta.
- Delivery: `scripts/guard.py` and `.github/workflows/guard.yml` are delivered files, so once this merges, a plan the
  owner approves delivers them to troupe-run/troupe and troupe-run/website. The website's specs aren't judged (not
  troupe). troupe's first run after delivery is a push to `main`, so it judges all 25 specs; they all name declared
  labels today, and a task checks that before the plan.
- No OpenTofu resource changes except the delivered files' content.
- #153 is closed by this change's pull request. #150 can close once it lands.
