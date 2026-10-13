# Design

## Context

See proposal.md for why. What shapes the approach:

- `tofu/labels/troupe.json` is read by OpenTofu into a `list(object({name, color, description}))` variable
  (`tofu/modules/repository/variables.tf`). The labels resource updates a changed description in place; it doesn't
  recreate the label or take it off issues.
- `scripts/oob.py` already reads troupe's spec folder list (`SPECS_GH_ARGS`) and reports a spec with no label. Its
  calls go through one `Fetch` that returns parsed JSON, and `test_every_github_call_is_a_read` refuses any call
  carrying `-H`, a method or a body.
- `oob/` holds the declarations `oob.py` checks GitHub against. `scripts/check.py` runs offline; `oob.py` needs the
  network and the owner's `gh`, and isn't run by CI.

Evidence read on 2026-10-13:

| | |
|---|---|
| Rows in #26's comment | 38, one per declared label except `cap:infrastructure` |
| Rows over 100 characters | 0. Every stated count matches the text |
| Labels with a troupe spec (14) | `actor-runners`, `artifact-store`, `cli`, `client-protocol`, `event-store`, `identity`, `lineage`, `platform`, `policy`, `runner-protocol`, `runs`, `scripted-runner`, `stages`, `vcs` |
| Spec-based rows checked against Purpose and spec body | all 14 fit. Terms not in a Purpose are in the spec body (JSON-RPC, JSON Schema, Docker, follow) or the cited issue (`policy`'s "tighten, never loosen" is troupe#8) |

## Goals / Non-Goals

**Goals:**
- A reader of the label picker can tell what each capability covers.
- When troupe changes what a spec says it's for, the owner hears about it where they already look for drift.

**Non-Goals:**
- Generating descriptions from troupe automatically. A Purpose runs to about 200 characters and has to be shortened
  by someone who reads it.
- Checking descriptions sourced from the glossary or issues (proposal, out of scope).

## Decisions

### D1. The recorded Purposes live in `oob/troupe-spec-purposes.json`, as text

A JSON object mapping each spec-based label to the Purpose it was written from:
`{"cap:runs": "Records each run of an actor …", …}`, one entry per label with a troupe spec, sorted by label name.
The text is the Purpose section with its whitespace collapsed to single spaces.

Text rather than a hash: when `oob.py` reports a change, the pull request that refreshes the record shows the old and
new Purpose side by side, which is what the reviewer needs to decide whether the description still fits. A hash would
detect the change but send them to troupe's history to see it. The snapshot is troupe's own words, copied only to
compare against, so it doesn't add product language of ours.

A separate file rather than an extra field in `troupe.json`: the labels variable is a fixed object type, and
OpenTofu silently drops attributes it doesn't declare. Keeping OpenTofu's input to exactly what it reads avoids a
field that looks like it reaches GitHub but doesn't. `oob/` is where `oob.py`'s declarations already live.

### D2. One read per spec, and two reports

`oob.py` fetches each labelled spec's `spec.md` with `gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md --jq '{content}'`,
which returns JSON (the base64 content) through the existing `Fetch`, with no `-H` and no method, so it stays a read.
It extracts the `## Purpose` section, up to the next `## ` heading, and collapses whitespace.

For each troupe spec that has a declared label:
- no entry in `troupe-spec-purposes.json` → `troupe labels: 'cap:<name>' description hasn't been checked against its spec's Purpose; record the Purpose in oob/troupe-spec-purposes.json`
- entry differs → `troupe labels: 'cap:<name>' spec's Purpose has changed; review its description in tofu/labels/troupe.json and update oob/troupe-spec-purposes.json`

A spec with no label is already reported by the existing check and isn't reported again. An entry for a label with
no spec on `main` is reported as extra, the same way `differences` reports a declaration missing on GitHub, so a
removed spec doesn't leave a record behind. `main`'s "no differences" line names the new check.

That's 14 more API calls per run. `oob.py` is run by hand alongside a plan, so the rate cost doesn't matter.

### D3. The offline test reads `troupe.json` directly

A new test in `scripts/tests/` (run by `scripts/check.py`) reads `tofu/labels/troupe.json` and fails, naming the
label, when a `cap:` description is over 100 characters or equals `Capability: <name>`. It's a test on the real file,
not a fixture, so it fails on the next pull request that adds a label the old way. GitHub would refuse an
over-length description only at apply time, after the merge.

`TBD` passes. Whether a capability is really undefined isn't something a test can know; the reviewer checks that.

## Risks / Trade-offs

- [Descriptions sourced from the glossary or issues drift unnoticed] → Accepted (proposal). When troupe writes
  those specs, D2's "not checked" report makes someone review the description.
- [A Purpose's Markdown changes, such as backticks added, with no change in meaning] → Reported as a change. The fix
  is one line in the record, and a false alarm is better than a missed change.
- [troupe stops using a `## Purpose` heading] → A spec with no Purpose section is reported as changed (empty Purpose),
  not skipped, following "a malformed input is an error".

## Migration Plan

One pull request: the descriptions, the record of all 14 Purposes, the check and the test. The owner approves the
plan (38 in-place description updates on troupe, nothing created or deleted), then merges and approves the apply.
Rollback is a revert; the next apply puts the old descriptions back, and no issue loses a label either way.
