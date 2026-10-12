# Tasks

## 1. The shared workflow labels (design D3)

- [x] 1.1 Create `tofu/labels/workflow.json` holding `needs:owner` exactly as `tofu/labels/troupe.json` has it
  (colour `D93F0B`, "Waiting on a decision from the owner"), and remove the entry from `troupe.json`. In
  `tofu/repositories.tf`, add `local.workflow_labels` and put it in every repository's `labels`, with a comment
  naming the `labels` spec. Verify:
  - `scripts/check.py` passes (`tofu fmt`, `tofu validate`, tests);
  - `grep -c '"needs:owner"' tofu/labels/*.json` finds it in `workflow.json` only.

  Extended during apply (owner, 2026-10-12): `parked` moved the same way (colour `C5DEF5`); `troupe.json` then holds
  only `cap:*` labels.

## 2. The templates (design D2, D4)

- [x] 2.1 Write `org-profile/.github/PULL_REQUEST_TEMPLATE.md`: troupe's template (design Context), with the D2
  source note as its first line and the last comment replaced by D4's wording. Verify: `git diff --no-index` against
  troupe's copy (fetched to the scratchpad with `gh api … -H "Accept: application/vnd.github.raw"`) shows only the
  note and that comment.
- [x] 2.2 Write `org-profile/.github/ISSUE_TEMPLATE/bug.yml`, `feature.yml`, `decision.yml` and `config.yml`: troupe's
  forms with D4's wording, the `cap:` line as D4 rewords it, and D2's YAML source note as each first line.
  `config.yml`: `blank_issues_enabled: true` and D4's contact link. Verify:
  - `git diff --no-index` against troupe's copies shows only D4's wording and the note;
  - no file names troupe except the `troupe --version` example (`grep -n -i troupe` over the four);
  - each file parses as YAML (`uv run --with pyyaml python -c …`, run once from the scratchpad, not added to the
    project).
- [x] 2.3 Write `scripts/tests/test_org_profile.py` (design D5), each test named for what its body checks:
  - each form's `type:` is an enabled type in `oob/issue-types.json`;
  - each label a form applies is in `tofu/labels/workflow.json`;
  - every file under `org-profile/` starts with the source note naming its own path (widened during apply from the
    new files only: the existing four already comply, and it is the same check);
  - a form with no `type:`, or that doesn't parse, fails, naming the form (a fixture in `tmp_path`);
  - a form naming an undeclared type, or an undeclared label, fails, naming both (fixtures in `tmp_path`).

  Verify: the tests pass; each failure test fails when the check it covers is removed (break it once, run, restore);
  `mypy --strict` and `ruff` are clean.

## 3. Publishing (design D1)

- [x] 3.1 In `tofu/org_profile.tf`, derive `org_profile_files` from `fileset("${path.module}/../org-profile", "**")`,
  excluding `.DS_Store`, and update the file's opening comment. Verify:
  - `scripts/check.py` passes;
  - `tofu console` lists the nine paths (the four existing, the five new);
  - `uv run scripts/oob.py` reports the five new files as declared here but missing on GitHub, and nothing else for
    `.github`.
- [x] 3.2 Add a short "Where the templates come from" section to `docs/development-workflow.md`: the PR template and
  issue forms are org defaults published from `org-profile/`; a repository with its own `.github/ISSUE_TEMPLATE/`
  uses none of the org's forms; a form's type and labels must be declared (D5). Verify: `scripts/check.py` passes,
  including `test_guard_docs.py`.

## 4. Land it

- [x] 4.1 Open the pull request (`Closes #19`, "Part of #15"; design D7). Its evidence:
  - the CI plan comment, after the owner approves the run. It must show five files created in `troupe-run/.github`,
    `needs:owner` and `parked` created in `infrastructure`, `.github` and `website`, and no change to the four
    existing files or to troupe's labels;
  - the test output.

  Verify: every required check is green on all three OSes, and the plan comment matches.

## Workflow follow-up

- Archive on the branch before the merge (`/opsx:archive`), syncing the `development-workflow`, `labels` and
  `org-profile` deltas.
- **After the owner merges and approves the apply:**
  - the five sync commits in `troupe-run/.github` are each named `chore: sync <path> <hash> from
    troupe-run/infrastructure`;
  - `uv run scripts/oob.py` reports no `.github` drift;
  - D6: on a throwaway `infra-probe-templates`, check the issue chooser (three forms, blank issue, security link) and
    a draft PR's description; file a Decision issue and check its type and `needs:owner`; delete the repository.
    Check `infrastructure`'s issue chooser, read only.
- Comment on #19 with the PR and the archived change (the merge closes it), and on #15 that part 1 is done. #15
  stays open for part 2.
- **Part 2, in troupe-run/troupe:** propose a change that deletes `.github/ISSUE_TEMPLATE/` and
  `.github/PULL_REQUEST_TEMPLATE.md`, with a PR that says `Closes troupe-run/infrastructure#15`.
