# Proposal

Issue: #63. This change does all of it, the three missing labels and `cap:releases`'s recorded Purpose, and
also fixes how troupe's issues are labelled, which the survey for #63 turned up (owner, 2026-10-18).

## Why

`scripts/oob.py` reports four differences for troupe's labels. They were first reported on 2026-10-16 (#63), and
were the same on 2026-10-18 against troupe's `main` at c0634ec:

- troupe's `flake-hunt`, `python-support` and `quality-check` specs have no `cap:` label, so issues for those
  capabilities can't be filed under one.
- troupe's `releases` spec has landed (troupe-run/troupe#23), and `cap:releases`, which refresh-cap-label-purposes
  declared ahead of the spec, has no recorded Purpose. Until it has one, `oob.py` can't tell when its description goes
  stale. That change (design D4) left this until `oob.py` asked for it, and `oob.py` now does.

While these four stand, `oob.py` can't report a clean result for troupe's labels, and a new drift would be hidden among
them.

A survey of troupe's open, closed and upcoming work for missing labels found no other capability that needs one: every
planned capability already has its label. But it found two labelling problems:

- **`cap:performance` has two meanings.** Its description is "One run of a process" (troupe's term), which is how #36
  uses it. But #54, #75, #108 and #109 use it to mean speed. There's no label for speed work, which exists in troupe
  (also #83, #84) and in infrastructure (#78).
- **Issues filed before their spec existed carry stand-in labels.** troupe's check and Python-version work carries
  `cap:infrastructure`, whose description is "the troupe-run org's own setup, not a troupe capability". troupe's
  flake-hunt work carries only `cap:platform`. #83 and #113 carry no `cap:` label at all.

## What Changes

- **Three capability labels are added** to `tofu/labels/troupe.json`, colour `1D76DB`, each with a description shortened
  from its spec's Purpose (design D1): `cap:flake-hunt`, `cap:python-support` and `cap:quality-check`.
- **Four Purposes are recorded** in `oob/troupe-spec-purposes.json`, verbatim with whitespace collapsed (design D2):
  the three above and `releases`. `cap:releases` keeps its description, which already says what its Purpose says
  (design D3).
- **A `speed` label is added for every managed repository**, in a new shared set `tofu/labels/kinds.json` for kinds
  of work that GitHub's default labels don't cover (design D4). `scripts/tests/test_labels.py` checks its descriptions'
  length.
- **troupe's issues are relabelled after the apply**, once the labels exist (design D5). Each issue gets the new labels
  that fit it. `cap:performance` comes off the four speed issues, and `cap:infrastructure` comes off troupe's own check
  and Python-version issues. infrastructure#78 gets `speed`.
- **No label is removed or renamed.** Taking a label off an issue doesn't change the declaration.

Out of scope:
- `scripts/oob.py` and `oob/README.md`, whose rules this change follows unchanged.
- Any change to troupe-run/troupe's files. Its only changes are labels on issues.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `labels`: adds a requirement that labels for kinds of work, such as `speed`, are declared once and given to every
  managed repository, and that a capability label isn't used to mark a kind of work. The rest of the change is data
  under the existing requirements "troupe's capability labels are declared here", "A troupe spec with no capability
  label is reported", "A capability label says what it covers" and "A description written from a spec records that
  spec's Purpose".

## Impact

- `tofu/labels/troupe.json`: three labels added, 40 → 43.
- `tofu/labels/kinds.json`: new, holding `speed`. `tofu/repositories.tf` adds it to all four repositories' label sets.
- `oob/troupe-spec-purposes.json`: four entries added, 15 → 19.
- `scripts/tests/test_labels.py`: also checks the kind labels' descriptions.
- GitHub, after the owner approves the plan: three labels created on troupe-run/troupe, and `speed` created on all
  four repositories. After that, 13 troupe issues and one infrastructure issue are relabelled (design D5).
- `scripts/oob.py` reports nothing for troupe's labels once this merges, until troupe's next spec change.
- #63 is closed by this change's pull request.
