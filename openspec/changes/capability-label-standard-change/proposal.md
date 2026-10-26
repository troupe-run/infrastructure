# Proposal

Issue: #152. Part of #150. Merges after #151 (design D5).

## Why

A new troupe capability label is a few lines of JSON in `tofu/labels/troupe.json`, but each one so far has gone
through the whole workflow worked out from scratch (#116, #132). troupe-run/troupe#169 made labels capabilities
rather than spec folders, so new ones will be rare, but #153 will send a change that needs one to "the standard
change that adds it", and that has to exist first.

The board's `Capability` field holds the same list a second time, by hand, and has already drifted: it has no `runs`
or `user-docs` option, and still has `lifecycle`, which troupe-run/troupe#169 removes. Nothing reports it.

## What Changes

- **A runbook, `docs/standard-changes.md`,** gives the steps for a new capability label as commands to run in order:
  check it isn't declared or under way, make the sub-issue (under the needing issue's Epic, in its milestone, on the
  board), the worktree and branch, the change through `/opsx:propose`, `/opsx:apply` and `/opsx:archive`, the pull
  request, and the steps after the merge. The sub-issue's body is the same steps as a checklist, so whoever runs it
  works down the ticket (design D1, D2).
- **The exact parts become checks, not generators.** `scripts/check.py` fails on a `troupe.json` that's out of byte
  order, a malformed `cap:` name, or a `cap:*` label with another colour. The description rules stay as they are
  (design D3).
- **The drift check compares the board's `Capability` options with the declared `cap:*` labels,** both ways
  (design D4).
- **The board is fixed before this merges, after #151:** the owner adds the options #151's list needs and removes
  `lifecycle`'s, since changing a field's options is owner-only (design D4, D5).
- `oob/README.md` points to the runbook for a new label, and lists the board check.

Out of scope:
- A skill or script that makes the change. Considered and dropped with the owner (design D1).
- Other standard changes (a milestone, a required check). The runbook has room for them.
- The guard finding a missing label at proposal (#153), and what #151 changes in the drift check and the labels.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `labels`: adds that a new capability label is a standard change, that troupe's labels are declared in one form,
  and that the board's `Capability` options match the labels.

## Impact

- New: `docs/standard-changes.md`.
- Changed: `scripts/tests/test_labels.py`, `scripts/oob.py`, `scripts/tests/test_oob.py`, `oob/README.md`, and
  `docs/development-workflow.md`'s pointer to the runbook.
- GitHub: no OpenTofu file changes, so the plan is empty. The owner changes the board's options by hand, as the drift
  check run on the branch lists them, before the merge, so the `drift (out of band)` job stays green.
