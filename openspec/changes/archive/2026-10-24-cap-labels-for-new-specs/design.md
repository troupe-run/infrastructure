# Design

## Context

See proposal.md for why. The approach is label-troupe-config-specs's (2026-10-23), with one difference: both specs
are already on troupe's `main`, so there is no merge order to manage and nothing to re-read later.

- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource. A new name is a label created on the next apply, and nothing else on the repository changes.
- `oob/troupe-spec-purposes.json` maps each `cap:<name>` with a troupe spec to that spec's Purpose as
  `scripts/oob.py`'s `purpose()` reads it. Both files are sorted by label name in byte order (`LC_ALL=C sort`:
  `cap:actor-runners` comes before `cap:actors`).
- `scripts/tests/test_labels.py` refuses a description over 100 characters, or one that only repeats the name.

Evidence read on 2026-10-24:

| | |
|---|---|
| `uv run scripts/oob.py` on `main` (0ed99cc) | the two differences in proposal.md, nothing else |
| `tofu/labels/troupe.json` | 46 labels, none for either spec |
| `oob/troupe-spec-purposes.json` | 23 entries, none for either spec |
| troupe's `openspec/specs/run-workspaces/spec.md` | 16 requirements, from troupe#51 |
| troupe's `openspec/specs/claude-code-runner/spec.md` | 30 requirements, from troupe#55 |

The two Purposes on troupe's `main`, as `purpose()` reads them:

- **run-workspaces:** "Defines where a run works, and what happens to what it changed. A run gets its own git
  worktree, where its changes are captured as a diff, and the person can see, accept or discard them, without
  anything the actor wrote reaching the theatre unasked."
- **claude-code-runner:** "Runs an actor through Claude Code. The runner speaks troupe's runner contract and maps
  Claude Code's stream-json onto run events, so `troupe perform` can use the engine troupe was designed around."

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing for troupe's labels once this is merged and applied.
- Each of the two specs has a label whose description was checked against its Purpose.

**Non-Goals:**
- Making the drift job tolerate a new spec until its label lands. A red job is how a missing label gets noticed, and
  it did its job here.
- Changing `cap:stages` or `cap:actor-runners`, whose descriptions still hold beside the new labels (D1).

## Decisions

### D1. The two descriptions

| Label | Description | Length |
|---|---|---|
| `cap:run-workspaces` | `Where a run works, in its own git worktree, and how its changes are seen, accepted or discarded` | 95 |
| `cap:claude-code-runner` | `Running an actor through Claude Code, mapping its stream-json onto run events` | 77 |

These are #132's wordings, made into sentences in the form of the other labels.

- **run-workspaces** keeps the Purpose's two halves: where a run works, and what becomes of its changes. "Captured as
  a diff" and "without anything reaching the theatre unasked" go, because 100 characters can't hold them, and they
  describe how accepting works rather than what the capability covers. It sits beside `cap:stages` ("Where an actor
  runs, and whether its effects can be enforced there"): a stage is the place and its enforcement, a workspace is the
  run's checkout and its changes. An issue about worktrees on the local stage carries both, as troupe#51 shows.
- **claude-code-runner** follows `cap:actor-runners`' "Running an actor through …" form, so the two read as general
  and particular. "So `troupe perform` can use the engine troupe was designed around" goes: it's why the runner
  exists, not what it covers.

Alternative: describe `cap:run-workspaces` from the Purpose's second sentence ("A run's own git worktree, its changes
captured as a diff, and…"). Rejected: it leaves out "where a run works", which is the part an issue about a cached
checkout (troupe#151) or a workspace provider (troupe#150) is about.

### D2. The record is the spec's text, verbatim

As in label-troupe-config-specs D2: each recorded Purpose is read through `purpose()` from troupe's `main`
(`gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md`), not copied from this design. In byte
order, `cap:claude-code-runner` goes before `cap:cli`, and `cap:run-workspaces` before `cap:runner-protocol`, in both
files.

### D3. Labelling troupe's issues

After the apply, once the labels exist, add each to the issues about its capability. No issue loses a label.

| Issue | Label | Why |
|---|---|---|
| troupe#51 "Local stage: a git worktree per run, so an actor's changes can be kept or discarded" (closed) | `cap:run-workspaces` | the issue the spec comes from |
| troupe#150 "Run workspaces: a base layer per commit, and a workspace provider seam?" | `cap:run-workspaces` | how a workspace is made |
| troupe#151 "Run worktrees from a cached checkout per commit, so large repos stay fast" | `cap:run-workspaces` | how a worktree is made |
| troupe#153 "Other ways to accept a run's changes: staged, committed, or a three-way merge" | `cap:run-workspaces` | accepting a run's changes |
| troupe#154 "A worktree run killed before its runner's init leaves a worktree no event names" | `cap:run-workspaces` | a worktree left behind |
| troupe#55 "Claude Code runner, with an opt-in live test" (closed) | `cap:claude-code-runner` | the issue the spec comes from |
| troupe#160 "Claude Code runner on a local model (Ollama, LM Studio): run an actor entirely offline" (closed) | `cap:claude-code-runner` | the Claude Code runner against another model |

Found by searching troupe's issues for worktree, workspace, accept, discard, Claude Code and stream-json. Left out:
#3 (effects on a local stage, not its workspace), #16 (which runner to build first), #56 and #162 (other runners),
and #11 and #65 (containers, not Claude Code).

## Risks / Trade-offs

- [troupe changes either Purpose before this merges] → 2.1 re-runs `oob.py` after a fast-forward onto `origin/main`
  and re-reads the specs; the record and description are updated together if either changed.
- [troupe adds another spec before this merges] → 2.1 stops if `oob.py` reports anything more, and the change is
  revised to cover it, or a new issue opened, rather than merged with the job still red.

## Migration Plan

The apply creates two labels. Rolling back is a revert of the pull request: the labels are deleted, and the `labels`
spec's "in use is never removed" rule then needs D3's labels taken off the issues first.
