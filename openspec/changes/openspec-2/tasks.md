# Tasks

## 1. Regenerate this repository's OpenSpec files

- [ ] 1.1 Verify `openspec --version` prints `2.0.0`. Run `openspec update --dry-run`, keep its list of 25 changes,
  and verify it lists no locally edited file to keep.
- [ ] 1.2 Run `openspec update`. Verify `git status --short` matches the dry run's list exactly (six
  `.agents/skills/openspec-*/SKILL.md` and `.agents/skills/.openspec-target` added, six `.claude/commands/opsx/*.md`
  deleted, six `.claude/skills/openspec-*` now relative links into `.agents/skills/`), that `openspec/config.yaml` and
  `.claude/settings.json` are unchanged, and that a second run changes nothing.

## 2. Move the pin and the guard's names

- [ ] 2.1 In `.github/workflows/guard.yml`, set `OPENSPEC_VERSION: 2.0.0`.
- [ ] 2.2 In `scripts/guard.py`, replace `/opsx:propose` with `/openspec-propose` in the `commit-branch-change` and
  `edit-branch-change` fixes and in `WORKFLOW_SUMMARY`, and `/opsx:apply` with `/openspec-apply-change` there (design
  D3). Update `test_a_branch_without_a_matching_change_is_refused` to expect `/openspec-propose add-thing`, and run it
  first against the old message to see it fail.
- [ ] 2.3 Re-capture `scripts/tests/fixtures/openspec-strict/{pass,fail}` with 2.0.0 (design D2): in a scratch copy
  of each fixture's `openspec/` tree run `openspec validate --all --strict --json --no-interactive` with
  `OPENSPEC_TELEMETRY=0`, replace the root path with `/probe/<name>`, and write `report.json`, `status` and `stderr`.
  Verify the diff against the 1.14.3 capture is only `durationMs`. Move `test_guard_openspec.py`'s docstring,
  `version=` values and expected messages from 1.14.3 to 2.0.0, and run it.

## 3. Rename the commands in the docs

- [ ] 3.1 In `CLAUDE.md` and `docs/standard-changes.md`, replace `/opsx:propose`, `/opsx:apply` and `/opsx:archive`
  with `/openspec-propose`, `/openspec-apply-change` and `/openspec-archive-change`, keeping lines within 120 columns.
  Verify `git grep -n '/opsx:' -- ':!openspec/changes' ':!scripts/tests/fixtures/plan-pr96.txt'` finds nothing.

## 4. Verify and commit

- [ ] 4.1 Run `openspec validate --all --strict` with 2.0.0 and verify it passes.
- [ ] 4.2 Run `uv run scripts/check.py` (load under ~40) and verify it passes. Commit, signed off.

## Workflow follow-up

- Open a draft pull request that says `Closes #308` and act on Claude's review. It merges only after troupe#423 and
  website#116 have merged (design D1).
- Before asking for the delivery plan's approval, run 2.0.0's `openspec validate --all --strict` over troupe's and
  website's `main` and name the result in the pull request.
- Archive the change on the branch before merging (no specs to sync).
- After the merge and the apply, check the delivered `guard.yml` in troupe and website pins 2.0.0, #308 is closed and
  its card says Done.
