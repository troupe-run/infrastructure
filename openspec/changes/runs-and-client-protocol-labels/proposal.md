# Proposal

Issue: #25. troupe's `perform-status-logs` change (troupe-run/troupe#36, PR troupe-run/troupe#52, merged 2026-10-12)
added four capabilities. Two of them, `stages` and `policy`, already have labels; `client-protocol` and `runs` don't.

## Why

troupe-run/troupe's `main` now has `openspec/specs/client-protocol/` and `openspec/specs/runs/`, and
`tofu/labels/troupe.json` has no `cap:client-protocol` or `cap:runs`. So there's no label to file troupe issues under
for either capability, and `scripts/oob.py` reports both specs as unlabelled, the way it caught `artifact-store`,
`runner-protocol` and `scripted-runner` after the runner contract (#22, #24). Checked on 2026-10-13: these are the only
two of troupe's 14 spec folders without a label.

## What Changes

- **Two labels are added** to `tofu/labels/troupe.json`: `cap:client-protocol` and `cap:runs`, colour `1D76DB`,
  description `Capability: <name>`, in name order, the same shape as the other 37 (design D1).
- **The owner approves the plan that creates them** on troupe-run/troupe, through CI's `apply` job after the merge.
- **troupe's issues get the new labels** once they exist, as #25's comment lists: `cap:runs` on troupe #3, #4, #33,
  #36, #51 and #54, and `cap:client-protocol` on #14, #33 and #36. PR troupe-run/troupe#52 is left out, since none of
  troupe's pull requests carry labels (design D2).
- **No label is removed or renamed.**

Out of scope:
- Any change to `scripts/oob.py`, the labels spec or the workflow's labels. The spec already says how a new capability
  gets its label ("troupe's capability labels are declared here"), and this change follows that path.
- Any change to troupe-run/troupe's files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a data change under the existing `labels` requirement "troupe's capability labels are declared here",
so the change sets `skip_specs: true`.

## Impact

- `tofu/labels/troupe.json`: two labels added, 37 → 39.
- GitHub, after the owner approves the plan: two labels created on troupe-run/troupe, nothing changed or deleted.
- troupe-run/troupe issues #3, #4, #14, #33, #36, #51 and #54: labels added. Four of them (#3, #4, #33, #36) are
  closed; adding a label doesn't reopen them.
- Once any issue carries them, the two labels fall under "A capability label in use is never removed or renamed".
