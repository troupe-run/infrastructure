# Proposal

Issue: #22 (step 6 of #1). The issue was parked waiting for troupe to define a capability list. The owner decided on
2026-10-12 that it won't: troupe's `cap:*` labels are declared here, in `tofu/labels/troupe.json`, and changed by pull
request when a capability is needed. This change makes that the rule and reconciles the list with troupe as it is
today.

## Why

`tofu/labels/troupe.json` was copied by hand from GitHub on 2026-10-11 as a stopgap, against the project constraint
"The capability list is read from there, never copied by hand". That constraint assumed troupe would keep a list to
read. It won't, so the constraint can never be met and #22 can never close. Meanwhile the copy has drifted from
troupe: three of troupe's ten specs (`artifact-store`, `runner-protocol`, `scripted-runner`) have no label to file
issues under.

## What Changes

- **The label file is the capability list.** `tofu/labels/troupe.json` stops being a copy awaiting replacement and
  becomes the declared set of troupe's capability labels. A new capability gets its label by a pull request here,
  like any other label change, and the owner approves the plan that creates it.
- **Three labels are added**, one per troupe spec that has none: `cap:artifact-store`, `cap:runner-protocol`,
  `cap:scripted-runner`, in the existing colour and description style (design D2).
- **No label is removed.** 25 of the 34 are on troupe issues today. The other nine (`actors`, `cues`, `escalation`,
  `flows`, `guests`, `lifecycle`, `notes`, `notifications`, `theatre`) are on no issue, but they name troupe's
  planned vocabulary (troupe-run/troupe#15), and whether a planned capability is dropped is troupe's call, not this
  repo's (design D3).
- **No label is renamed.** The labels resource is authoritative, so a rename is a delete and a create, and deleting
  a label takes it off every issue that carries it (design D2).
- **The project constraint is rewritten** in `openspec/config.yaml` to say where troupe's capability labels are
  declared and how they change, with the decision's date and issue, and the stale comment in
  `tofu/repositories.tf` goes.
- **`scripts/oob.py` reports a troupe spec with no `cap:` label.** It reads troupe's `openspec/specs/` folders from
  GitHub and names each one with no matching label in `troupe.json`. A label with no spec is not reported: a label can
  come before its spec (design D4).
- **Docs say how to add one:** the README's label row, `oob/README.md`'s check table, and the org's Feature and
  Decision forms, which today say only "add a `cap:` label if the repository has them" (design D5).
- **`parked` comes off #22**, since it is no longer waiting on troupe.

Out of scope:
- The workflow's labels (`needs:owner`, `parked`) in `tofu/labels/workflow.json`.
- Any change in troupe-run/troupe: troupe's specs and issues are read, never written.
- Making the spec check part of `scripts/check.py` or CI. It needs the network, and the check must work offline.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `labels`: troupe's capability labels are declared here and changed by pull request; a label still in use is never
  removed or renamed; a troupe spec with no label is reported.

## Impact

- `tofu/labels/troupe.json` (three labels added), `tofu/repositories.tf` (comment).
- `openspec/config.yaml` (constraint), `openspec/specs/labels/spec.md` (on archive).
- `scripts/oob.py` and `scripts/tests/test_oob.py` (the new check), `oob/README.md`.
- `org-profile/.github/ISSUE_TEMPLATE/feature.yml` and `decision.yml`, published to `troupe-run/.github`.
- `README.md`.
- GitHub, after the owner approves the plan: three labels created on troupe-run/troupe; a commit to
  troupe-run/.github for the two forms. Nothing deleted.
