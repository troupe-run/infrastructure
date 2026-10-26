# Design

## Context

See proposal.md for why. Read on 2026-10-26:

- `tofu/labels/troupe.json` holds 48 `cap:*` labels in byte order (`LC_ALL=C sort`), all colour `1D76DB` but
  `cap:infrastructure` (`5319E7`).
  OpenTofu manages them as one authoritative `github_issue_labels` resource, so a new label shows in the plan as
  `module.repo_troupe.github_issue_labels.this` updated in place with one `+ label` block (#133's plan comment).
- `scripts/tests/test_labels.py` checks each description: at most 100 characters, not `Capability: <name>`. Byte
  order and colour have been checked by hand in each change's tasks (#133's 1.2).
- The guard enforces the workflow's shape already: no commit without a change named like the branch, no archive with
  an unticked task, no pull request without `Closes #n` (spec: development-workflow). What it can't check is the
  label's own values, and where its sub-issue goes.
- The board's `Capability` field is a single-select with 34 options: the 48 labels without the 12 spec-level ones
  troupe-run/troupe#169 folds, and without `runs` and `user-docs`, which #169 keeps. 21 cards set it; none is
  `lifecycle`. Nothing declares the field, and the guard makes `updateProjectV2Field`, `gh project create` and
  `gh project field-*` owner-only (`scripts/guard.py`).
- `scripts/oob.py` already reads the org's projects with GraphQL, in CI with the infrastructure App's "Projects: read".
- troupe-run/troupe#170 is closed, so #151, which changes the label list to 36, is no longer blocked.

## Goals / Non-Goals

**Goals:**
- A label goes from "needed" to an approvable pull request by steps anyone can run quickly from the ticket.
- Every exact value the steps produce is checked by something that fails, not trusted to the person or agent.
- The board's list can't drift from the labels again without the drift check saying so.

**Non-Goals:**
- Automating the steps. Revisit if labels turn out not to be rare.
- Managing the board's field in OpenTofu, which can't (the provider has only classic Projects).

## Decisions

### D1. A runbook, not a skill or a template

The first proposal of this change had a skill run the steps and a script render the change from a template, with
`/opsx:propose` told to keep the template's text. The owner and I dropped it (2026-10-26): propose would have
decided nothing, a byte-for-byte check of its output against a template is brittle, and six subcommands, a template,
a plan parser and a test keeping the skill and script in step are a lot to build for a few labels a year.

Instead, `docs/standard-changes.md` has a "Capability label" section of commands in order, with `<name>`,
`<description>` and `<issue>` as the only blanks, and the same steps as a checklist for the sub-issue's body. The
change is proposed, applied and archived with the real skills. It is small enough that they do it in minutes:
`skip_specs: true`, one task to add the label and run the checks, as #116 and #133 were.

Alternative: an issue form for the sub-issue. Rejected for now: forms are org defaults published to every repository
(spec: development-workflow), and this is only ever filed here.

### D2. What the steps say

1. **Check it isn't done:** `cap:<name>` in `origin/main:tofu/labels/troupe.json`, an open issue here titled
   ``Add the `cap:<name>` capability label``, or a branch or pull request `add-cap-<name>-label`. Any of them: stop
   and point the needing issue at it.
2. **The sub-issue:** a Task here with that title and the checklist as its body, `--project "troupe roadmap"`, in the
   needing issue's milestone (every listed repository has the same milestones). Its parent is the needing issue's
   Epic when it has one, the needing issue otherwise. The needing issue is marked blocked by it: that records which
   issue to label after the apply when the parent is the Epic, and what #153's refusal can point to.
3. **The worktree:** `git worktree add ../infrastructure-add-cap-<name>-label -b add-cap-<name>-label origin/main`,
   card to In Progress.
4. **The change:** `/opsx:propose add-cap-<name>-label` with `skip_specs: true`, `/opsx:apply` (add the label in byte
   order, `uv run scripts/check.py`, `uv run scripts/oob.py` reporting nothing about the label), `/opsx:archive`.
5. **The pull request,** opened after the archive with `Closes #<sub>` through `--body-file`, so the owner approves
   one `plan-pr` run. Its plan should show the labels resource changed in place with one `+ label` block and nothing
   else; read it and say so on the pull request.
6. **Just before the merge,** once the plan is approved: the owner adds `<name>` to the board's `Capability` field
   (D4), then merges.
7. **After the merge and the apply:** the label on the needing issue with `gh issue edit --add-label`, the sub-issue
   closed if the merge didn't, its card Done, and the comment.

Step 6 sits before the merge because the board check reads the declared labels, not GitHub's: the `drift (out of
band)` job runs straight after each merge, and an option added only after it would leave that run red, hiding any
other drift (#132). Added just before the merge, the option is ahead of `main` only for the minutes until the merge,
when a scheduled run is unlikely; the check would report it then as an option with no label, which the merge clears.
(Raised by a side agent during apply, 2026-10-26.)

Probed on 2026-10-26 (task 1.1) with two private throwaway repositories, `troupe-run/infra-probe-20261026-a` (the
label's repository, with milestone `0.1.0`) and `-b` (the needing issue's), deleted afterwards. Auto mode refused
creating public ones, and nothing probed depends on visibility. Each command succeeded:

```
gh issue create -R troupe-run/infra-probe-20261026-b --title "probe epic" --type Epic …            → b#1
gh issue create -R troupe-run/infra-probe-20261026-b --title "probe needing issue" --type Feature … → b#2
gh issue create -R troupe-run/infra-probe-20261026-a --title 'Add the `cap:probe` capability label' --type Task --milestone 0.1.0 … → a#1
gh issue edit 1 -R troupe-run/infra-probe-20261026-b --add-sub-issue <b#2 url>,<a#1 url>
gh issue edit 2 -R troupe-run/infra-probe-20261026-b --add-blocked-by <a#1 url>
```

Read back: `a#1` is a Task in `0.1.0` with parent `b#1`; `b#2`'s `dependencies/blocked_by` lists `a#1`, and `a#1`'s
`dependencies/blocking` lists `b#2`. So step 7 finds the needing issue from the sub-issue with
`gh api repos/troupe-run/infrastructure/issues/<sub>/dependencies/blocking`.

Step 4's `oob.py` run is where anything else a label needs shows up, such as a record #151 leaves in place. The
runbook says to follow `oob/README.md` then, and writes nothing about those records itself, since #151 is changing
them.

### D3. The exact parts are checks

`test_labels.py` gains three tests over `troupe.json`: names in byte order (reporting the first pair out of order),
the name form (`cap:` then lowercase letters and digits, words joined by single hyphens), and the colour `1D76DB`
for every `cap:*` label but `cap:infrastructure`. That one is `5319E7`, adopted so (fc9157d) because it marks the
org's own setup, "not a troupe capability", and it stays the only exception, named in the test with that reason.
All 48 labels meet the three rules today (checked 2026-10-26 with `LC_ALL=C sort -c` and `jq`).

### D4. The board's options are checked, and changed by the owner in the board's settings

A new `oob.py` check, "board capabilities", reads the field's options with GraphQL
(`organization.projectV2(number: 1).field(name: "Capability")`, its `options { name }`) and compares them with the
declared `cap:*` names without the prefix. The declaration is derived from `troupe.json`, as the `troupe specs`
check's is, so there is no second list to keep. A missing field, or one that isn't a single-select, is a difference
naming it, not a pass.

The owner adds or removes an option in the board's field settings on GitHub. Not through `updateProjectV2Field`:
it takes the whole option list, and whether it keeps the cards' values when options are replaced is unknown and
can't be tested without an owner-made throwaway project. Adding one option in the UI touches no card. Removing
`lifecycle` clears nothing, since no card has it.

### D5. Merge after #151

Merged now, the check would report the 12 spec-level labels #151 folds. Adding their options and removing them again
writes what #151 undoes, and an exception list is a second list that #151 must delete. So this change is built and
reviewed now, and merged once #151 has merged and applied. Before the merge, on the branch fast-forwarded onto
`origin/main`, `oob.py` lists what the board still needs; the owner fixes it, and `oob.py` is run again.

If #151's labels-spec delta archives first, this change's `labels` delta is still ADDED requirements only, so it
syncs without conflict.

## Risks / Trade-offs

- [A step is skipped] → The guard refuses the workflow's missing steps; `check.py` and `oob.py` refuse wrong
  values. What's left unchecked is the sub-issue's parent and milestone, and the after-merge labelling, which the
  checklist holds and the comment reports.
- [#151 takes longer than expected] → The change waits on its branch. Nothing in it is urgent once troupe#169 makes
  new labels rare; the board's drift is visible meanwhile in this change's own `oob.py` run.
- [GitHub refuses a sub-issue here under a troupe Epic, or a cross-repository blocked-by] → Probed on two
  `infra-probe-*` repositories (task 1.1) before the runbook says to do it.

## Migration Plan

No OpenTofu change, so nothing is applied. The board's options are fixed by hand before the merge (D5). Rolling back
is a revert; the board's options can stay, as they match the labels.

## Open Questions

None.
