# Proposal

Issue: #116.

## Why

troupe's `config-model` change (troupe-run/troupe#60, branch `config-model`, not yet merged) adds two specs, `config`
and `config-files`. Once it reaches troupe's `main`, `uv run scripts/oob.py` reports `config-files` as having no
`cap:` label, and `cap:config` as a labelled spec with no recorded Purpose. The `drift (out of band)` job fails on
both until this lands, the way it did for `user-docs` and `docs-publishing` (#112).

#116 asks only for `cap:config-files`, described `Capability: config-files`. That shape predates the
`labels` spec's description rules: a description now says what the capability covers, and one written from a spec
records that spec's Purpose. Those rules also reach `cap:config`. Its description today, "Config files under
.troupe/: layout, per-file schemas, the hand-edit sweep and write-back", describes what `config-files` now covers,
and says nothing of what the `config` spec does (config as events, merged across branches, and the actor).

## What Changes

- **`cap:config-files` is added** to `tofu/labels/troupe.json`, colour `1D76DB`, with a description shortened from
  its spec's Purpose (design D1).
- **`cap:config`'s description is rewritten** from the `config` spec's Purpose (design D1). The label keeps its name
  and colour.
- **Both Purposes are recorded** in `oob/troupe-spec-purposes.json`, verbatim with whitespace collapsed, read from
  the `config-model` branch now and checked against troupe's `main` once #60 merges (design D2).
- **troupe's config-file issues get `cap:config-files` after the apply** (design D3). None loses `cap:config`.
- **No label is removed or renamed.**

**Merge order:** troupe#60 first, then this (design D4). Until #60 merges, `oob.py` on this branch reports the two
recorded Purposes as having no spec. That's expected, and the pull request waits for it to clear.

Out of scope:
- `scripts/oob.py` and `oob/README.md`, whose rules this change follows unchanged.
- The roadmap board's Capability field, as #116 says.
- Any change to troupe-run/troupe's files. Its only changes are labels on issues.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is data under the `labels` spec's existing requirements: "troupe's capability labels are declared here",
"A troupe spec with no capability label is reported", "A capability label says what it covers" and "A description
written from a spec records that spec's Purpose". So the change sets `skip_specs`, as label-troupe-docs-specs did.

## Impact

- `tofu/labels/troupe.json`: one label added (45 → 46), one description changed.
- `oob/troupe-spec-purposes.json`: two entries added (21 → 23).
- GitHub, after the owner approves the plan: `cap:config-files` created and `cap:config`'s description updated on
  troupe-run/troupe. After that, five troupe issues get `cap:config-files`.
- The drift job passes once both troupe#60 and this are on their `main`s and applied.
- #116 is closed by this change's pull request.
