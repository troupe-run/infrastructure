# Proposal

Issue: #26. The issue's comment (owner, 2026-10-13) gives a description for each of troupe's `cap:` labels and picks
option 1: shorten each spec's Purpose here, and have `scripts/oob.py` report when that Purpose changes.

## Why

38 of troupe's 39 `cap:` labels have the description `Capability: <name>`, which only repeats the name. Someone
filing or triaging a troupe issue can't tell from the label picker what `cap:lineage` or `cap:stages` covers without
opening the spec. A description written from a spec also goes stale silently when troupe rewrites the spec, so it
needs a check that says when.

## What Changes

- **38 descriptions are replaced** in `tofu/labels/troupe.json` with the text from #26's comment. Each is 100
  characters or fewer (GitHub's limit) and says what the capability covers. `cap:infrastructure` keeps the
  description it already has. The plan updates each label in place, so no label is removed or taken off any issue.
- **`TBD` for undefined capabilities.** `cap:flows` and `cap:lifecycle` have no spec, glossary entry or issue that
  defines them, so their description is `TBD` until troupe does (owner, 2026-10-13), rather than a guess.
- **Each description written from a spec records the Purpose it was written from**, verbatim, in a new declaration
  under `oob/` (design D1).
- **`scripts/oob.py` reports a description that may be stale:** a troupe spec whose Purpose differs from the one
  recorded for its label, and a labelled spec with no Purpose recorded at all. Each report names the label and says
  to review the description and update the record by pull request (design D2).
- **An offline test checks the descriptions** in `scripts/check.py`: every `cap:` description is 100 characters or
  fewer, and none is the bare `Capability: <name>` (design D3).
- **Docs:** `oob/README.md`'s check table gets a row for the new check, and says how a new capability's label gets
  its description.

Out of scope:
- Guidance on when to apply each label. It won't fit in 100 characters alongside what the label means, and it
  belongs in troupe's own contributing guide or forms if anywhere.
- A staleness check for descriptions written from the glossary or an issue rather than a spec. `oob.py` reads only
  troupe's specs. Those labels are reviewed when their spec arrives, since the new check then reports them as having
  no recorded Purpose.
- Renaming or removing a label, colours, and the workflow's labels.
- Any change in troupe-run/troupe.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `labels`: troupe's capability labels carry descriptions that say what they cover, and a description that may have
  gone stale against its spec's Purpose is reported.

## Impact

- `tofu/labels/troupe.json`: 38 descriptions changed.
- `oob/`: a new declaration of the Purpose each spec-based description was written from. `oob/README.md` updated.
- `scripts/oob.py`, `scripts/tests/test_oob.py`: the new check, plus one read of each troupe spec's `spec.md`.
- A new offline test for the descriptions under `scripts/tests/`.
- `openspec/specs/labels/spec.md` (on archive).
- GitHub, after the owner approves the plan: 38 labels on troupe-run/troupe get new descriptions. Nothing is created
  or deleted, and no issue loses a label.
