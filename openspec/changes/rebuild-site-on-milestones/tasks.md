# Tasks

## 0. The owner's decisions

- [x] 0.1 Owner: confirm design D1 (reuse `troupe-run-docs`, or a new App) and record it in design.md as
      "(owner, <date>)". Verify that D1's heading no longer says "the owner confirms". Done: option A, reuse
      `troupe-run-docs` (owner, 2026-10-25), and D1's heading says so
- [x] 0.2 Open a troupe-run/website issue to name infrastructure's milestones notice as a second sender in its
      `build-and-deploy` spec and `deploy.yml` header, documentation only (design D7), on the roadmap board. Verify
      with `gh issue view <n> -R troupe-run/website --json projectItems`, and link it from D7. Done: website#47, on
      the board as Todo, linked from D7

## 1. infrastructure's `docs` environment

- [x] 1.1 Add `("repo_infrastructure", "docs"): False` to `MAIN_ONLY` in
      `scripts/tests/test_main_only_environments.py` (design D4). Verify that
      `uv run pytest scripts/tests/test_main_only_environments.py` fails, naming `docs on repo_infrastructure` as not
      declared, before 1.2
- [x] 1.2 In `tofu/docs.tf`, declare `docs_infrastructure` on `module.repo_infrastructure` (`can_admins_bypass =
      false`, `prevent_self_review = false`, no reviewers, custom branch policies), its `main`-only policy
      `docs_infrastructure_main_only`, and `docs_app_client_id_infrastructure`, from `local.docs_app_client_id`, and
      name both users in the header (design D6). Verify that the test from 1.1 passes and `uv run scripts/check.py`
      passes (tofu fmt, validate)
- [x] 1.3 Check the test catches weakening on infrastructure, not only troupe: on a scratch copy, set the new
      environment's `can_admins_bypass = true`, and separately its policy's `branch_pattern` to `*`. Verify the test
      fails each time, naming `docs on repo_infrastructure` and what changed, then restore the file
- [x] 1.4 Update `oob/README.md`'s docs App section: the key's second home, the `gh secret set DOCS_APP_PRIVATE_KEY
      --env docs -R troupe-run/infrastructure` command fed by `op read -n`, its check by name, and rotation running both
      commands. Update `openspec/specs/docs-build-credentials/spec.md`'s Purpose to say troupe and infrastructure, and
      README.md's `tofu/docs.tf` row. Verify `uv run scripts/check.py` passes
- [x] 1.5 Added during the probe (owner, 2026-10-25): make every documented `op read` into `gh secret set` set
      nothing when the read fails, in `oob/README.md` (release, board, docs) and README.md (the tofu workflow's four
      secrets). Piped, a timed-out 1Password approval still ran `gh` and set an empty secret on the probe. Verify each
      command reads into a variable joined to `gh` by `&&`, and `uv run scripts/check.py` passes. Done: b9a75ed

## 2. The notice workflow

- [x] 2.1 Write `scripts/tests/test_milestones_notice_workflow.py` (design D4): `problems()` over the loaded workflow,
      a test that the real file has none, and a parametrised test that each weakening listed in D4 is named. Verify
      that `uv run pytest scripts/tests/test_milestones_notice_workflow.py` fails because the workflow doesn't exist,
      before 2.2
- [x] 2.2 Add `.github/workflows/milestones-notice.yml` (design D2, D3), with a header comment naming the spec
      (milestones, docs-build-credentials) and #124. Verify the tests from 2.1 pass, and that each mutation in the
      parametrised test is reported by a `problems()` message that names it
- [x] 2.3 Add the workflow to README.md's layout table. Verify `uv run scripts/check.py` passes, including
      `test_required_checks.py` unchanged

## 3. Probe the path filter (design D5)

- [x] 3.1 Create `troupe-run/infra-probe-milestones-notice` with a stub `deploy.yml` (`on: workflow_dispatch`, one
      job that echoes), a `tofu/milestones.json`, a `docs` environment limited to `main` with `DOCS_APP_PRIVATE_KEY`
      set from 1Password (printing nothing) and `DOCS_APP_CLIENT_ID` set, the docs App added to the probe for the
      probe, and this change's workflow with only the target repository changed. Verify the environment's secret
      lists by name and the App's installation includes the probe
- [x] 3.2 Push to `main` a change to `tofu/milestones.json`. Verify the notice run succeeds and a stub deploy run
      starts on `main` with event `workflow_dispatch`
- [x] 3.3 Push to `main` a change to another file, and push to a branch a change to `tofu/milestones.json`. Verify
      neither starts a notice run (`gh run list -R troupe-run/infra-probe-milestones-notice -w milestones-notice.yml`)
- [ ] 3.4 Record the findings with run IDs under design D5, then remove the probe from the App's installation and
      delete the repository. Verify the repository is gone and the docs App's installation lists `website` only

## 4. The pull request

- [ ] 4.1 Open the pull request with `Closes #124`, the decisions from group 0, the website issue from 0.2 and the
      probe's findings. Verify CI's plan on it shows only infrastructure's `docs` environment, its deployment policy
      and `DOCS_APP_CLIENT_ID` being created, and nothing changed or destroyed

## Workflow follow-up

- Archive the change on the branch, rebase onto main's latest state commit, then ask for the plan approval once.
- After the merge and the apply: the owner sets `DOCS_APP_PRIVATE_KEY` on infrastructure's `docs` environment, and
  it's checked by name.
- Check the merge's own push started no `milestones-notice` run. At the next push that changes
  `tofu/milestones.json`, check the notice run and the website Deploy run on `main`.
- Comment on #124 with the PR, the archived change and those runs (or that the first is still to come). Check that
  #124 is closed and its card says Done. Delete the worktree and branch.
