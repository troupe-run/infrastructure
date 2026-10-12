# Design

## Context

See proposal.md for why. What shapes the approach:

- troupe-run/troupe's labels come from `tofu/labels/troupe.json` (with the GitHub defaults and the workflow's labels)
  through an authoritative `github_issue_labels` resource. A label exists on GitHub only once the owner approves the
  plan that creates it, so the issue labelling in D2 has to wait for the apply.
- The guard refuses `gh label create` from Claude (`owner-only`), but allows adding an existing label to an issue
  (`repos/…/issues/<n>/labels`, POST), which is a workflow write.

Evidence read on 2026-10-13:

| | |
|---|---|
| troupe's spec folders on `main` (14) | `actor-runners`, `artifact-store`, `cli`, `client-protocol`, `event-store`, `identity`, `lineage`, `platform`, `policy`, `runner-protocol`, `runs`, `scripted-runner`, `stages`, `vcs` |
| Spec with no label (2) | `client-protocol`, `runs` |
| Declared labels | 37 |

The troupe issues #25's comment names, and the `cap:` labels they carry now:

| Issue | State | Gets |
|---|---|---|
| #3 Effects on a local stage | closed | `cap:runs` |
| #4 Actor transcripts | closed | `cap:runs` |
| #14 The run server | open | `cap:client-protocol` |
| #33 Walking skeleton | closed | `cap:runs`, `cap:client-protocol` |
| #36 troupe perform, status and logs | closed | `cap:runs`, `cap:client-protocol` |
| #51 Local stage: a git worktree per run | open | `cap:runs` |
| #54 Wake on new events with OS file watching | open | `cap:runs` |

None of them carries either label yet.

## Goals / Non-Goals

**Goals:**
- `scripts/oob.py` reports no unlabelled troupe spec once the plan is applied.
- The issues that are about runs or the client protocol can be found by those labels.

**Non-Goals:**
- Reviewing the `cap:` labels on any other troupe issue. #25's comment already did that sweep on 2026-10-12.
- Better label descriptions than `Capability: <name>`.

## Decisions

### D1. Same shape and order as the existing labels

Each label is `{"name": "cap:<name>", "color": "1D76DB", "description": "Capability: <name>"}`, inserted so the file
stays sorted by name: `cap:client-protocol` after `cap:cli`, and `cap:runs` after `cap:runner-protocol`. This matches the
capability-labels change's D2 and every label in the file. A distinct colour or a longer description was considered
and rejected: it would make two labels unlike the other 37 for no reader's benefit.

### D2. Label troupe's issues after the apply, as part of this change

The labels can't be applied to issues until the owner's approved apply creates them. They are applied after that,
with `gh issue edit --add-label`, and before the follow-up comment on #25. This is a small write to troupe's issue
metadata, not its files, so it doesn't fall under "changes to a product repo's files arrive as pull requests". The
list is #25's comment. The alternative, leaving it to troupe, was rejected: #25's comment says nothing else will
apply them.

PR troupe-run/troupe#52 is left unlabelled, as #25's comment says, since none of troupe's pull requests carry labels.

## Risks / Trade-offs

- [The plan shows more than two labels changing, for example drift made by hand since the last apply] → The plan is
  read before the pull request is opened. Anything beyond the two creations is reported to the owner, not folded
  into this change.
- [troupe adds another spec before this merges] → `oob.py` is run again right before the follow-up on #25. A new
  unlabelled spec gets its own issue, not a silent addition here.
- [Labelling a closed issue notifies its subscribers] → Accepted. It's what #25 asks for, and it's a one-off.

## Migration Plan

The pull request's plan is approved by the owner. After the merge, the owner approves the `apply` job, which creates
the two labels. Then the issues are labelled (D2) and `oob.py` is run. To roll back, revert the commit: the next apply
deletes both labels, which takes them off every issue. That's why "a capability label in use is never removed"
applies once D2 is done.
