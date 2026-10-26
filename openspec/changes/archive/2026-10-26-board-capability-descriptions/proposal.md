# Proposal

## Why

On 2026-10-26, 35 of the 36 options of the troupe roadmap board's `Capability` field had no description, so the
board's filters explained only `infrastructure` (#166). The options were made by hand with names only. #152's drift
check compares their names with troupe's `cap:*` labels but not their descriptions, so a new label's option starts
blank, and a label's description can change while the board's goes stale. The owner decided on 2026-10-26 that the
descriptions are managed from this repository, from the labels they mirror.

## What Changes

- **The plan of `main` shows the board's description changes.** A new script, `scripts/board_options.py`, reads the
  `Capability` field and `tofu/labels/troupe.json`, and lists each option whose description differs from its label's.
  The plan job shows the list in its summary, and a non-empty list waits for the owner's approval like an OpenTofu
  change, even when OpenTofu has none.
- **After the approved apply, a new `board` job sends them.** In infrastructure's existing `board` environment, with
  the troupe-run-board App's token, it re-reads the field, refuses if it changed since the plan, and sends every
  option back with its id, name and colour, in its order, changing only descriptions. It refuses rather than send an
  option without its id, since `updateProjectV2Field` replaces the whole list and an option sent without one clears
  every card's value for it.
- **The drift check compares descriptions too.** `scripts/oob.py`'s "board capabilities" check also reports each
  option whose description differs from its label's, naming it.
- **Options are still added and removed by the owner,** by hand in the field's settings, as #152's standard change
  says. The sync never creates or removes an option (design D5).
- **Before the first live run, a probe** on a throwaway project the owner creates shows that the sync keeps an item's
  value for the field (design D6).
- `oob/README.md` and `docs/standard-changes.md` say where the descriptions come from, and that the next apply after
  a new label's merge gives its option its description.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `labels`: two added requirements. The board's `Capability` options carry their labels' descriptions, given them by
  an apply the owner approved, keeping every option's identity; and the drift check reports an option whose
  description differs.

## Impact

- New `scripts/board_options.py` and its tests in `scripts/tests/`.
- `.github/workflows/tofu.yml`: the `plan` job runs the script's `plan` with its read-only token and counts its
  changes; a new `board` job after `apply` runs the script's `apply` in the `board` environment.
- `scripts/oob.py`: the board query reads `description`, and the check compares it.
- `tofu/` is unchanged: the provider has no Projects v2 resource. The board App's permissions are unchanged ("Projects:
  read and write" already covers a field's options). infrastructure's `board` environment and its key exist (#60).
- The first apply after the merge changes all 36 descriptions (a dry run on 2026-10-26 found 36 options, every name
  matching a label; the one described, `infrastructure`, differs from its label's). No card's `Capability` value may
  change.
- Arose from #152. Part of #150.
