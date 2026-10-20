# Proposal

Issue: #112.

## Why

troupe's `user-docs` and `docs-publishing` specs reached its `main` on 2026-10-19 (troupe `ed518b2` and `16e3ed7`)
with no `cap:` label. So issues for those capabilities can't be filed under one, and the `drift (out of band)` job
has failed on every run since (first seen in run 39360548729). `uv run scripts/oob.py` on `main` reports these two
and nothing else. While it's red, a new drift would be hidden behind them.

## What Changes

- **Two capability labels are added** to `tofu/labels/troupe.json`, colour `1D76DB`, each with a description shortened
  from its spec's Purpose (design D1): `cap:user-docs` and `cap:docs-publishing`.
- **Their two Purposes are recorded** in `oob/troupe-spec-purposes.json`, verbatim with whitespace collapsed
  (design D2).
- **troupe's docs issues are relabelled after the apply** (design D3). troupe#120 and #123 were filed before these
  specs existed and carry stand-ins.
- **No label is removed or renamed.**

Out of scope:
- `scripts/oob.py` and `oob/README.md`, whose rules this change follows unchanged.
- Any change to troupe-run/troupe's files. Its only changes are labels on issues.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "troupe's capability labels are declared here",
"A troupe spec with no capability label is reported", "A capability label says what it covers" and "A description
written from a spec records that spec's Purpose". So the change sets `skip_specs`, as runs-and-client-protocol-labels
did.

## Impact

- `tofu/labels/troupe.json`: two labels added, 43 → 45.
- `oob/troupe-spec-purposes.json`: two entries added, 19 → 21.
- GitHub, after the owner approves the plan: two labels created on troupe-run/troupe. After that, troupe#120 and #123
  are relabelled.
- The drift job passes again once this is applied.
- #112 is closed by this change's pull request.
