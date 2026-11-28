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

## 4. Rollout

- [ ] 4.1 The pull request's plan shows only the three `AUTO_MERGE` variables changing; the owner approves it
- [ ] 4.2 After the merge, main's apply sets them (owner approves), and the next `auto-merge.yml` run queues what qualifies and comments nothing
