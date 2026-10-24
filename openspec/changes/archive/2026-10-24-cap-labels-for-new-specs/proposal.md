# Proposal

Issue: #132.

## Why

troupe-run/troupe#51 (worktree-stage) and troupe-run/troupe#55 (claude-code-runner) archived two new specs into
troupe's `openspec/specs/`, `run-workspaces` and `claude-code-runner`, with no `cap:` label declared for either.
`uv run scripts/oob.py` on `main` (0ed99cc) now reports:

```
troupe specs: 'claude-code-runner' has no cap:claude-code-runner label; add it to tofu/labels/troupe.json by pull request
troupe specs: 'run-workspaces' has no cap:run-workspaces label; add it to tofu/labels/troupe.json by pull request
oob: 2 difference(s). Fix GitHub, or update the declaration in oob/.
```

The `drift (out of band)` job has failed on this since the scheduled run of 2026-10-23, and while it's red it can't
show anything else that drifts.

## What Changes

- **`cap:run-workspaces` and `cap:claude-code-runner` are added** to `tofu/labels/troupe.json`, colour `1D76DB`,
  each with a description shortened from its spec's Purpose (design D1).
- **Both Purposes are recorded** in `oob/troupe-spec-purposes.json`, verbatim with whitespace collapsed, read from
  troupe's `main` through `scripts/oob.py`'s `purpose()` (design D2). Without the record, `oob.py` would trade each
  "no label" difference for a "no recorded Purpose" one.
- **The troupe issues about each capability get its label after the apply** (design D3). No issue loses a label.
- **No label is removed, renamed or re-described.**

Out of scope:
- `scripts/oob.py` and `oob/README.md`, whose rules this change follows unchanged.
- Re-reading the Purposes of specs that #51 and #55 modified rather than added. `oob.py` reports nothing for them
  today.
- The roadmap board's Capability field.
- Any change to troupe-run/troupe's files. Its only changes are labels on issues.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "troupe's capability labels are declared here",
"A troupe spec with no capability label is reported", "A capability label says what it covers" and "A description
written from a spec records that spec's Purpose". So the change sets `skip_specs`, as label-troupe-config-specs did.

## Impact

- `tofu/labels/troupe.json`: two labels added (46 → 48).
- `oob/troupe-spec-purposes.json`: two entries added (23 → 25).
- GitHub, after the owner approves the plan: the two labels created on troupe-run/troupe, and nothing else. After
  that, seven troupe issues get one of the new labels.
- The drift job's `troupe specs` differences clear once this is merged and applied.
- #132 is closed by this change's pull request.
