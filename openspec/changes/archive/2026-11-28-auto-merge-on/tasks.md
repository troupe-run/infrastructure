## 1. The switch

- [x] 1.1 Add a test that reads `tofu/auto_merge.tf` and fails unless `auto_merge_switches` is troupe, infrastructure and website, all `on`; run it and see it fail on `dry-run`
- [x] 1.2 Set the three switches to `on` in `tofu/auto_merge.tf` and update its comment; the test passes
- [x] 1.3 Change the dry-run comment's closing line in `scripts/auto_merge.py` (marker unchanged) and any test that checks it

## 2. #363

- [x] 2.1 Make the workflow test's permission mapping skip `actions_variables`, saying why; see it fail while the input is still in the workflow
- [x] 2.2 Drop `permission-actions-variables: read` from `.github/workflows/auto-merge.yml`; the test passes

## 3. Docs

- [x] 3.1 Say in `docs/development-workflow.md` ("The switch") and `README.md` that it's `on` in all three, `off` the break-glass, `dry-run` still a valid value
- [x] 3.2 `uv run scripts/check.py` passes

## Workflow follow-up

- Open the draft pull request with `Closes #320` and `Closes #363`. Archive the change before marking it ready.
- The pull request's plan shows only the three `AUTO_MERGE` variables changing, `dry-run` to `on`; the owner approves it.
- The owner merges by rebase, through the merge queue, then approves main's apply.
- The next `auto-merge.yml` run's summary shows `(on)` for all three repositories, queues what qualifies and comments
  nothing; no repository shows an `error` reading its switch (#363).
- Check #320 and #363 are closed and their cards say Done; comment on each with the pull request and the archived change.
