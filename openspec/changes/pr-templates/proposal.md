# Proposal

Issue: #15 (raised as troupe-run/troupe#32 and transferred here). This change is part 1 of the issue's delivery
plan: specify the templates here and publish them to `troupe-run/.github`. Part 2, deleting troupe's own copies so
the org defaults apply, is a change in troupe-run/troupe. This part is tracked as sub-issue #19, which this PR
closes (design D7).

## Why

troupe's PR template still says "After merge: archive the change", the order from before the workflow settled.
Today the change is archived on its branch before the merge, and the merge closes the issue. The PR template and the
issue forms are process, but they stayed in troupe when #25 / troupe-run/troupe#30 moved the process here. Nothing
ties them to the `development-workflow` spec, so they drifted. Every other repository the org builds in has none.

## What Changes

- **Five new files in `org-profile/`**, published to `troupe-run/.github` like `CONTRIBUTING.md`:
  - `.github/PULL_REQUEST_TEMPLATE.md`: troupe's, with its last comment corrected to the settled order: archive on
    the branch before merging; after the merge, comment on the issue with the PR and the archived change.
  - `.github/ISSUE_TEMPLATE/bug.yml`, `feature.yml`, `decision.yml`: troupe's forms, reworded to suit any repository
    (the issue's wording; design D4).
  - `.github/ISSUE_TEMPLATE/config.yml`: blank issues on, plus a contact link to the security policy.
- **GitHub uses org-default issue forms only in a repository with no `.github/ISSUE_TEMPLATE/` of its own**, so every
  form moves, not just the PR template. A repository with its own folder keeps it.
- **Each file carries the source note** that `org-profile` requires, in a form GitHub doesn't render: a YAML comment
  in the forms, an HTML comment in the PR template (design D2).
- **`tofu/org_profile.tf` derives its file list from `org-profile/`**, so a new source file can't be left unpublished
  (design D1).
- **`needs:owner` becomes a label in every managed repository.** The Decision form applies it, and today only troupe
  has it. It moves from troupe's label list to a list every repository shares (design D3).
- **A test ties the forms to what they need:** each form's `type:` is an issue type declared in `oob/issue-types.json`,
  and each label a form applies is in the shared list (design D5).

Out of scope:
- **Deleting troupe's `.github/ISSUE_TEMPLATE/` and `PULL_REQUEST_TEMPLATE.md`.** That is part 2, a pull request
  through troupe's own checks. Until it lands, troupe keeps its stale copies.
- **Enforcing that a PR follows the template.** The guard already checks the closing reference.
- **Rewording `CONTRIBUTING.md`.** It already describes the settled order.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- **`development-workflow`:** a new requirement, "The workflow's templates are org defaults": the PR template and
  issue forms are published from here and state the workflow's order.
- **`labels`:** a new requirement, "Every managed repository has the workflow's labels".
- **`org-profile`:** "Each file in .github says where it is changed" gains a scenario for the PR template, whose note
  is copied into each new PR's description without being rendered.

## Impact

- **Changed:** `org-profile/.github/` (five new files), `tofu/org_profile.tf`, `tofu/repositories.tf`,
  `tofu/labels/` (a new shared list; `needs:owner` leaves `troupe.json`), `scripts/tests/` (a new test),
  `docs/development-workflow.md` (where the templates live).
- **Applied, after the owner approves the plan:** five commits by the App to `troupe-run/.github`; `needs:owner`
  created in `infrastructure`, `.github` and `website`. troupe's `needs:owner` is unchanged (the same label, declared
  from a different list).
- **Every repository in the org without its own templates** (`infrastructure`, `.github`, `website`, and any new
  repository) gets the PR template and the Bug, Feature and Decision forms. `website` has its own `CONTRIBUTING.md`
  but no templates, so it gets these too.
- **troupe:** nothing changes until part 2 removes its copies.
