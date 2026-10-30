# Standard changes

A standard change is a routine change whose steps are written here once, so it goes the same way every time and
nothing in it is decided afresh. It still follows the workflow every change follows (an issue, an OpenSpec change on
its branch, a pull request that closes the issue, the archive before the merge), and the guard refuses the same
steps it always does. What it adds is the exact commands, and checks that refuse a wrong value. The owner's part is
approving the pull request's plan, merging it and approving the apply, plus anything only the owner can do, named in
the steps.

Each section's steps are also its sub-issue's checklist, so whoever runs them works down the ticket.

Today there is one: [a capability label](#a-capability-label) (spec: `labels`, #152).

## A capability label

troupe's issues are labelled by capability, `cap:<name>`, declared in `tofu/labels/troupe.json` and changed only by
pull request here (spec: `labels`). Use these steps when a troupe change needs a capability that has no label yet.

The blanks:

| Blank | Example | What it is |
|---|---|---|
| `<name>` | `workspaces` | the capability: lowercase letters and digits, words joined by single hyphens |
| `<description>` | `Where a run works and how its changes are kept` | at most 100 characters, saying what the capability covers; `TBD` if troupe hasn't defined it |
| `<repo>`, `<n>` | `troupe`, `42` | the issue that needs the label |

Run the steps from this repository's main checkout, except where they say the worktree.

### 1. Check it isn't done already

```sh
git fetch origin
git show origin/main:tofu/labels/troupe.json | jq -e --arg label "cap:<name>" 'any(.[]; .name == $label)'
gh issue list -R troupe-run/infrastructure --state open --search 'in:title "cap:<name>"'
git ls-remote --heads origin add-cap-<name>-label
gh pr list -R troupe-run/infrastructure --head add-cap-<name>-label --state open
```

`jq` prints `true` if the label is already declared. If it is, or any of the others lists something, stop: point the
needing issue at the label, the issue or the pull request, and make nothing.

Then read the needing issue. It must be open:

```sh
gh api repos/troupe-run/<repo>/issues/<n> --jq '{state, milestone: .milestone.title}'
gh api repos/troupe-run/<repo>/issues/<n>/parent --jq '{parent: .html_url, type: .type.name}'
```

The second prints the issue's parent, or fails with `No parent issue found (HTTP 404)` if it has none.

### 2. The sub-issue

Write the checklist at the end of this page to `sub-issue.md` with the blanks filled, then:

```sh
gh issue create -R troupe-run/infrastructure --type Task --project "troupe roadmap" \
  --title 'Add the `cap:<name>` capability label' --body-file sub-issue.md --milestone "<milestone>"
```

`<milestone>` is the needing issue's (every repository has the same milestones): the needing issue is blocked by
the sub-issue, so its release waits for the label too. Leave `--milestone` out if it has none, since then no release
waits for either, and say so on the sub-issue. Call the new issue `<sub>`. Then link it:

```sh
gh issue edit <parent> -R troupe-run/<repo> --add-sub-issue https://github.com/troupe-run/infrastructure/issues/<sub>
gh issue edit <n> -R troupe-run/<repo> --add-blocked-by https://github.com/troupe-run/infrastructure/issues/<sub>
```

`<parent>` is the needing issue's parent if that parent's type is `Epic`, and the needing issue itself otherwise.
The blocked-by link is how step 7 finds the issue to label. Check the card is on the board:

```sh
gh issue view <sub> -R troupe-run/infrastructure --json projectItems
```

### 3. The worktree

```sh
git worktree add ../infrastructure-add-cap-<name>-label -b add-cap-<name>-label origin/main
gh project item-edit 1 --owner troupe-run --url https://github.com/troupe-run/infrastructure/issues/<sub> \
  --field Status --value "In Progress"
```

Everything from here to step 5 runs in the worktree.

### 4. The change

`/opsx:propose add-cap-<name>-label`, giving it the label, the description and both issues. It's a change with
`skip_specs: true`, because a new label is data under the `labels` spec's existing requirements: a proposal saying
why the capability needs a label and quoting the description, and one task:

> Add `cap:<name>` to `tofu/labels/troupe.json`, colour `1D76DB`, with the description, in byte order. Verify
> `git diff` shows only that label, `uv run scripts/check.py` passes, and `uv run scripts/oob.py` reports nothing
> about `cap:<name>` except the board's missing `<name>` option, which step 6 adds.

If `oob.py` reports anything else about the label, follow [oob/README.md](../oob/README.md) for it, in the same
change. If the label would need a requirement changed, it isn't a standard change: stop and propose it the usual
way.

Then `/opsx:apply`, and `/opsx:archive`, each committed as the workflow says.

### 5. The pull request

Push, and open the pull request after the archive, so the owner approves one `plan-pr` run instead of two:

```sh
git push -u origin add-cap-<name>-label
gh pr create -R troupe-run/infrastructure --title "feat(labels): declare cap:<name> for troupe-run/<repo>#<n>" \
  --body-file pr.md
```

`pr.md` says `Closes #<sub>`, quotes the description and its length, and pastes the output of `check.py` and
`oob.py`. Once the owner approves the plan run, read its comment: it should be for the branch's head commit, say
`Plan: 0 to add, 1 to change, 0 to destroy.`, and show `module.repo_troupe.github_issue_labels.this` gaining one
`+ label` block with the declared name, colour and description, and nothing else. Say on the pull request that it
does, or what it shows instead.

### 6. The board's option, then the merge (the owner)

Just before merging, the owner adds `<name>` to the `Capability` field in the troupe roadmap board's settings, with
the label's description, copied from the pull request. Adding or removing a field's options is owner-only, and done
in the settings rather than through the API, which replaces the whole option list. It comes before the merge because
the drift check runs straight after it and compares the field's options and their descriptions with the declared
labels: added later, or without the description, that run would go red and hide any other drift (#132). If the
description is left out or differs, the plan made at the merge lists it, and the apply's `board` job sets it from
the label (spec: labels).

Then the owner merges by rebase, through the merge queue, reads the `plan (main)` plan, and approves the apply.

### 7. After the apply

```sh
gh label list -R troupe-run/troupe --search "cap:<name>"
gh api repos/troupe-run/infrastructure/issues/<sub>/dependencies/blocking --jq '.[].html_url'
gh issue edit <n> -R troupe-run/<repo> --add-label "cap:<name>"
gh issue view <n> -R troupe-run/<repo> --json labels
```

The first shows the label exists, the second names the needing issue, and the last shows it carries the label beside
its others. The `drift (out of band)` job of that run, or `uv run scripts/oob.py`, should report nothing about the
board: the option is there with the label's description, set by the owner in step 6 or by the `board` job. Then check the sub-issue is closed (`gh issue close <sub> -R troupe-run/infrastructure` if the merge
didn't), and its card says Done:

```sh
gh issue view <sub> -R troupe-run/infrastructure --json state,projectItems
gh project item-edit 1 --owner troupe-run --url https://github.com/troupe-run/infrastructure/issues/<sub> \
  --field Status --value "Done"
```

Finish with `gh issue comment <sub> -R troupe-run/infrastructure` naming the pull request and the archived change.
Remove the worktree and branch once that's done.

### The sub-issue's checklist

```markdown
Needed by troupe-run/<repo>#<n>. Made from docs/standard-changes.md ("A capability label").

| Label | Description | Length |
|---|---|---|
| `cap:<name>` | <description> | <length> |

- [ ] 1. Not declared on `main`, and no open issue, branch or pull request adds it
- [ ] 2. This issue: a Task, on the board, in the needing issue's milestone, under its Epic (or the issue), blocking it
- [ ] 3. Worktree and branch `add-cap-<name>-label`; card In Progress
- [ ] 4. Change `add-cap-<name>-label` proposed, applied and archived; `check.py` and `oob.py` clean but for the board option
- [ ] 5. Pull request opened after the archive; its plan shows only the label added
- [ ] 6. Owner: `<name>` added to the board's Capability field with the label's description, then merged and applied
- [ ] 7. Label on troupe-run/<repo>#<n>; the drift check reports nothing about the board; this issue closed and Done; comment with the pull request and the archived change
```
