# Design

## Context

See proposal.md for why. Read on 2026-10-26, on infrastructure `main` at 255ee24 (after #160's apply) and troupe's
`main`:

| | |
|---|---|
| `tofu/labels/troupe.json` | 49 labels, including the 12 folded ones, `cap:lifecycle` and `cap:development` |
| troupe's specs | 25, each naming its labels in a well-formed `Capability:` line, matching troupe#169's table row for row (#160, task 5.2) |
| troupe issues carrying a folded label | 59 label uses on 43 issues, 14 open and 29 closed. #151's comment says "59 issues"; it counted uses, not issues |
| troupe pull requests carrying one | none |
| `cap:lifecycle` | on nothing |
| Labels to add | 43, on 36 issues. #14, #36, #64, #150, #151, #153 and #160 already carry every label their specs name |
| Files naming a folded label | `tofu/labels/troupe.json` only, outside `openspec/` (here and on troupe's `main`) |
| `oob/` | `troupe-spec-purposes.json` is keyed by spec (25 specs, all still in troupe). No file is keyed by a label |
| The board's `Capability` field | no option for a folded label; a `lifecycle` option, on no card (#152's design) |

The edits per issue, from the mapping each spec's `Capability:` line gives (✓ = already carries every label):

| Folded label | Spec names | Issues |
|---|---|---|
| `cap:claude-code-runner` | `cap:actor-runners` | 55, 160 |
| `cap:scripted-runner` | `cap:actor-runners` | 16, 33, 34, 58, 76, 155 |
| `cap:runner-protocol` | `cap:actor-runners`, `cap:protocol` | 16, 33, 34, 55, 56, 70, 76, 155, 162 |
| `cap:run-workspaces` | `cap:stages`, `cap:vcs` | 51, 150, 151, 153, 154 |
| `cap:config-files` | `cap:config`, `cap:projections` | 5, 6, 60, 119, 138, 156 |
| `cap:artifact-store` | `cap:storage` | 4, 33, 34, 51 |
| `cap:client-protocol` | `cap:core-api`, `cap:protocol` | 14, 33, 36, 64, 70, 73, 76, 122 |
| `cap:flake-hunt` | `cap:development` | 100, 112 |
| `cap:python-support` | `cap:development` | 104, 105, 107 |
| `cap:quality-check` | `cap:development` | 83, 101, 108, 109, 155 |
| `cap:releases` | `cap:development` | 23, 104, 105, 107, 139, 140, 143, 144 |
| `cap:docs-publishing` | `cap:development`, `cap:user-docs` | 120 |

The additions this gives, by label, leaving out issues that already carry it:

| Label to add | Issues |
|---|---|
| `cap:actor-runners` | 58, 70, 76, 155 |
| `cap:protocol` | 16, 55, 56, 73, 122, 155, 162 |
| `cap:vcs` | 154 |
| `cap:projections` | 5, 6, 60, 119, 138, 156 |
| `cap:config` | 156 |
| `cap:storage` | 4, 33, 34, 51 |
| `cap:core-api` | 70, 73, 76, 122 |
| `cap:development` | 23, 83, 100, 101, 104, 105, 107, 108, 109, 112, 120, 139, 140, 143, 144, 155 |

That's 43. Nothing to add for `cap:stages` or `cap:user-docs`: every issue that needs them has them.

## Goals / Non-Goals

**Goals:**
- No issue loses a capability: at no moment is an issue without a label its folded label stood for.
- The plan the owner approves deletes 13 labels that are on nothing, and changes nothing else.
- What was edited is recorded, so the relabel can be checked or undone issue by issue.

**Non-Goals:**
- A reusable relabel tool. Folds are rare (#169 is the first), and the spec now says what a fold must do.
- Re-reading troupe#169's table. The specs' `Capability:` lines are the mapping; #160 checked they match it.

## Decisions

### D1. The mapping is read from the specs, at apply

The labels each folded label becomes are read from troupe's `main` at apply time, with `scripts/oob.py`'s
`spec_documents` and `capability_labels` (the parser the drift check uses), not typed in from #169's table or this
design. The tables above are what that read gave on 2026-10-26. If troupe's lines have changed since, the read wins and
the difference is recorded in the task. Rejected: a hand-written mapping, which is the second list #169 decided
against.

### D2. Every label the spec names, and nothing taken off but the folded label

Per #169: an issue gets every label its folded label's spec names, even one that may not fit, because trimming is a
later edit while a lost label can't be recovered. The relabel never removes any other label, and adds only labels
already declared and on GitHub. For an issue with several folded labels, it gets the union.

### D3. Two passes with `gh issue edit`: all additions, a check, then all removals

1. **Inventory**, read-only: list every troupe issue and pull request, open and closed, with its labels; compute the
   additions and removals from D1; write them to `relabel.md` in this change, as tables like the ones above, with the
   exact commands.
2. **Add**, one `gh issue edit <n>... -R troupe-run/troupe --add-label <label>` per label to add, naming every issue
   that needs it (`gh issue edit` takes several issues). 8 commands for 43 additions.
3. **Check** against GitHub that every issue carrying a folded label now carries every label its spec names. Stop
   if not.
4. **Remove**, one `gh issue edit <n>... --remove-label <folded>` per folded label. 12 commands for 59 removals.
5. **Check** that no issue or pull request carries any of the 13 labels, and that each of the 43 issues carries
   exactly the labels it had before, minus its folded labels, plus its additions.

Run as plain `gh issue edit` commands in the shell, not from a script, so each write goes through the guard's
`gh issue edit --add-label`/`--remove-label` route, the one way the guard allows (`scripts/guard.py`). Adding before
removing means an interruption leaves an issue with too many labels, never too few. Rejected: one `--add-label` and
`--remove-label` per issue (43 commands, and an interrupted command could leave an issue with neither), and a
`removed` label taking issues off by the apply's deletion (that's the "label in use" removal the spec forbids).

Before the edits, the "before" labels of the 43 issues are saved in `relabel.md`, so any issue can be put back.

### D4. The declaration change and its plan

The 13 entries are deleted from `tofu/labels/troupe.json`, leaving 36, still in byte order. The plan is expected as
`Plan: 0 to add, 1 to change, 0 to destroy.`, with `module.repo_troupe.github_issue_labels.this` updated in place
and exactly 13 `label` elements removed: no element added and no other element changed. The pull request lists, for
each of the 13, the troupe issues and pull requests that carry it, read from GitHub when it's opened: none (spec:
"A capability label in use is never removed or renamed").

### D5. No oob record to clear

The request was to clear any oob records keyed by a removed label. There are none: #160 re-keyed
`oob/troupe-spec-purposes.json` by spec, and the specs whose labels fold (`artifact-store`, `config-files` and the
others) still exist, so their recorded Purposes stay. No other `oob/` file names a `cap:` label. The apply checks this
again with `git grep` rather than relying on this design. The drift check's `troupe specs` needs no change: no spec
names a removed label, and #160 already ignores a declared label no spec names.

## Risks / Trade-offs

- [A folded label is put on an issue between the relabel and the apply] → nothing in troupe applies them (no template
  or workflow names one, checked on troupe's `main`), so only a person could. Step 5's check is run again just before
  opening the pull request and before asking for the plan's approval, and any issue found is relabelled the same way.
- [An issue gets a label that doesn't fit, such as `cap:protocol` on an issue only about the runner] → #169 accepted
  this; it's a later edit by whoever owns the issue.
- [Label edits bump each issue's update time, including 29 closed issues] → no notification is sent for a label
  change, and the board isn't affected.
- [#152 is built in parallel and touches the labels spec and `oob.py`] → its delta is ADDED-only and its design
  merges it after this (its D5), so both sync without conflict. Rebase onto `main` before archiving if it lands
  first.
- [Undoing it] → reverting the pull request re-creates the 13 labels empty. Putting them back on issues uses the
  "before" record in `relabel.md`.

## Migration Plan

1. Apply's relabel (D3), then the declaration change, then the PR (`Closes #151`) with the plan as evidence.
2. Archive on the branch, rebase onto `main`'s state commit, ask once for the plan's approval.
3. The owner merges and approves the apply: the 13 labels are deleted on troupe-run/troupe.
4. After the apply: the troupe label list has 36 `cap:` labels, the drift job shows nothing new, #151 is commented on
   and closed, and its card says Done. Tell #152's session that the labels are final, so it can fix the board's
   `lifecycle` option and merge.
