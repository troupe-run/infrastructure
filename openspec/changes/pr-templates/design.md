# Design

## Context

- **How `.github`'s files are published** (spec: `org-profile`): `tofu/org_profile.tf` lists four paths under
  `org-profile/` and writes each to `troupe-run/.github` with `github_repository_file`, as the App. Each commit
  message carries a hash of the content, so a sync never reuses an earlier message. The drift check
  (`scripts/oob.py`) already derives its list from every file under `org-profile/`, so it picks up new files with no
  change. `scripts/plan_needed.py` already treats any change under `org-profile/` as needing a plan.
- **troupe's templates today** (troupe `main`, read 2026-10-12): `.github/PULL_REQUEST_TEMPLATE.md` and
  `.github/ISSUE_TEMPLATE/{bug,feature,decision,config}.yml`. `bug.yml` and `feature.yml` name troupe ("troupe does
  something…", "a theatre", `troupe --version`). `feature.yml` and `decision.yml` say to add `cap:<capability>`
  labels, which only troupe has.
- **How GitHub applies org defaults:** a repository uses the `.github` repository's `.github/ISSUE_TEMPLATE/` only
  if it has no `.github/ISSUE_TEMPLATE/` folder of its own, including a lone `config.yml`. The PR template is
  decided separately: a repository with its own `PULL_REQUEST_TEMPLATE.md` uses that.
- **What the forms need from the org:**
  - Issue types Bug, Feature and Decision exist and are enabled (`oob/issue-types.json`, checked against GitHub by
    `scripts/oob.py`).
  - The Decision form applies `needs:owner`. Of the managed repositories, only troupe has it (`tofu/labels/troupe.json`).
    `infrastructure`, `.github` and `website` have GitHub's defaults only (`tofu/repositories.tf`).
- **Who gets the defaults:** `infrastructure`, `.github` and `website` have no templates today, so all three start
  using them on apply. troupe keeps its own until part 2 of #15.

## Goals / Non-Goals

**Goals:**
- One source for the PR template and issue forms, published like the other `.github` files and checked for drift.
- What a form needs from the org (an issue type, a label) is declared, and a missing one fails the checks here, not
  silently on GitHub.

**Non-Goals:**
- Per-repository templates. A repository that needs its own adds a folder, and then owns all of its forms.
- Changing troupe's files. Part 2, through troupe's own checks.

## Decisions

### D1. The published list is derived from `org-profile/`

`org_profile_files` becomes `fileset("${path.module}/../org-profile", "**")`, leaving out any `.DS_Store`. Checked
with `tofu console` on 2026-10-12: `fileset` includes dot-directories and returns the same four keys as today's list,
so the existing resources keep their addresses and the plan for them is empty.

**Why:** a file added under `org-profile/` but forgotten in the list would be reported by the drift check as
unexpected on GitHub only after someone noticed it missing. Deriving the list matches how `oob.py` already reads it.

**`.DS_Store` is excluded** because `fileset` reads the disk, not git. CI's checkout has none, but a local plan on
macOS could otherwise propose publishing one.

**Alternative: extend the explicit list to nine paths.** Simple, but it's the second list to keep in step that the
derived drift check was written to avoid.

### D2. The source note in each new file

`org-profile` requires a note that GitHub doesn't render:
- **Issue forms:** a first-line YAML comment, as in `.github/dco.yml`: `# Source: troupe-run/infrastructure
  (org-profile/.github/ISSUE_TEMPLATE/bug.yml). Change it there; this copy is written by the App.` GitHub ignores
  comments when it builds the form.
- **PR template:** a first-line HTML comment, as in `CONTRIBUTING.md`. GitHub copies the template into each new PR's
  description, so the note travels into every PR body. It isn't rendered, and the template's guidance is already
  HTML comments, so it reads as one more of them.

**Alternative for the PR template: no note.** That breaks `org-profile`'s requirement for one file. The cost of the
note is a line of hidden text in each PR description, which is acceptable.

### D3. `needs:owner` moves to a shared list every repository gets

A new `tofu/labels/workflow.json` holds `needs:owner` (colour `D93F0B`, "Waiting on a decision from the owner", as
troupe has it). `tofu/repositories.tf` gains `local.workflow_labels`, and each repository's `labels` becomes
`concat(local.github_default_labels, local.workflow_labels, …)`. The entry leaves `troupe.json`, so troupe declares
it once.

**Why one list:** the label is the workflow's, not troupe's. A future workflow label is added in one place.

**troupe's plan stays empty for this label:** same name, colour and description. The module writes all of a
repository's labels as one `github_issue_labels` resource, keyed by name (`tofu/modules/repository/main.tf`), so
moving the entry between lists changes nothing GitHub sees. The plan is the proof.

**Alternative: drop `labels:` from the Decision form.** GitHub skips a label that doesn't exist, so the form would
still work, but a Decision issue would lose the marker the owner filters on.

### D4. Wording for any repository

As the issue gives it:
- `bug.yml` description: "Something doesn't do what it should, or what its specs say."; repro: "The smallest setup
  and commands that show it."; version: "The version or commit (for example `troupe --version`), and your OS."
- `feature.yml` description: "Something a project should do. Becomes one OpenSpec change."
- `decision.yml` and `config.yml` as the issue says; `config.yml`'s contact link is named "Report a vulnerability",
  points to `https://github.com/troupe-run/.github/blob/main/SECURITY.md`, and says to report privately.
- **PR template:** troupe's, with the last comment replaced by: "Archive the change on this branch before merging.
  After the merge, comment on the issue with this PR and the archived change."

**One addition to the issue's wording:** the "Add a `cap:<capability>` label…" line in `feature.yml` and
`decision.yml` becomes "If the repository has `cap:<capability>` labels, add one for each capability this touches."
Only troupe has them; unchanged, the line would ask for labels that don't exist elsewhere. This keeps the line
meaningful in troupe and harmless everywhere else.

### D5. A test ties each form to the org

`scripts/tests/test_org_profile.py` reads each `org-profile/.github/ISSUE_TEMPLATE/*.yml` other than `config.yml`
and checks:
- it has a top-level `type:` naming an enabled type in `oob/issue-types.json`;
- every label in its top-level `labels:` is in `tofu/labels/workflow.json`;
- its first line is the source note naming its own path.

Standard library only, so the top-level keys are read line by line (`^type: `, `^labels: [...]`), and a form whose
keys can't be read that way fails with its name rather than passing. `oob.py` already proves
`oob/issue-types.json` matches GitHub, so the chain reaches the org.

**Alternative: a YAML parser.** The guard's scripts are standard library only, and three top-level keys don't need
one.

### D6. Verifying GitHub's behaviour

After the apply, on a throwaway repository `infra-probe-templates` in `troupe-run` (no templates of its own): open
the issue chooser and a draft PR, and check the three forms, the blank issue, the security link and the PR
template. File one Decision issue and check its type and label. Then delete the repository. The live repositories
are only read: `infrastructure`'s issue chooser shows the forms.

### D7. How this PR references #15 (open: needs the owner)

The issue's plan says this PR says "Part of #15", so #15 stays open until troupe's part lands. The guard's
`pr-closes-issue` rule refuses a PR into this repository without a closing keyword, so "Part of #15" alone can't be
opened from a session. Options:
- **A. A sub-issue of #15 for this part** ("Publish the PR template and issue forms as org defaults"); this PR
  `Closes` it and says "Part of #15". troupe's PR closes #15. Fits the rule and the issue's intent. *Recommended.*
- **B. This PR closes #15,** and part 2 gets its own issue in troupe. Simpler, but #15 closes while troupe's copies
  are still stale, which is the problem #15 reports.
- **C. The owner grants a one-use override** of `pr-closes-issue` for this PR. Uses the break-glass for a routine
  case.

## Risks / Trade-offs

- **[Website gets forms that mention OpenSpec and specs]** → It has its own `CONTRIBUTING.md` and no OpenSpec today.
  The wording is general enough to file an issue against, and the website can add its own folder later (Open
  Questions).
- **[The security link may duplicate GitHub's own]** → GitHub adds its own "Report a security vulnerability" entry
  when private vulnerability reporting is on. Both lead to the same policy; D6 checks how the chooser looks.
- **[The PR template's note shows in raw PR bodies]** → Hidden when rendered; D2.
- **[troupe stays stale until part 2]** → Its local copies win until deleted. Part 2 is the next change on the plan.

## Migration Plan

1. Merge; CI's plan shows five file creations in `.github`, `needs:owner` created in three repositories, and no
   change to the existing four files or troupe's labels.
2. The owner approves the apply. D6 verifies on a throwaway repository.
3. Part 2 in troupe deletes its templates, and the org defaults apply there.

Rollback: revert the commit and apply. The provider deletes the five files from `.github` and the label from the
three repositories (no issue uses it there yet).

## Open Questions

- Whether `website` should keep the org's forms or carry its own. Deferrable: it changes only the website's repo.
