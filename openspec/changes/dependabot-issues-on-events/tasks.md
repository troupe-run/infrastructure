# Tasks

## 1. The dispatch App, and what GitHub allows (design D1, D2, Migration 1–2)

- [x] 1.1 Ask the owner to create `troupe-run-dispatch` with Actions read/write and Metadata read, no organisation
  permission and no webhook, installed on infrastructure and a throwaway `troupe-run/infra-probe-dependabot-dispatch`.
  Verify the installation exists in the org's App list, and record the App's ID and client ID on #195.
- [x] 1.2 Probe `workflow_run` of "Dependabot Updates" on a public throwaway `troupe-run/infra-probe-dependabot-events`.
  Set it up with an old `npm` dependency, a `.github/dependabot.yml`, a main-only environment holding a dummy secret,
  and a workflow on `workflow_run: workflows: ["Dependabot Updates"], types: [completed]`. The workflow uses that
  environment and prints only whether the secret is non-empty. Verify with `gh run list` that it runs after
  Dependabot's run, on `main`, and that the secret is readable. Then comment `@dependabot rebase` on a pull request
  that's behind `main`, and verify it runs again. Record the run URLs and results in design.md (Risks). **If it
  doesn't fire or gets no secret, stop and ask the owner with the findings (D1).**
- [x] 1.3 Probe the dispatch with the App's token, minted with `repositories: infra-probe-dependabot-dispatch` and
  `permission-actions: write`. Verify `gh workflow run` starts a `workflow_dispatch` run there. Verify creating a
  branch, a file and an issue there is refused with 403, and so is starting a workflow in the events probe repository.
  Record the results in design.md (Risks).
- [x] 1.4 Remove the probe repositories from the App's installation and delete them. Verify `gh repo view` fails for
  both, and the App's installation lists infrastructure only.

## 2. The credential declarations (spec dependabot-dispatch-credentials; design D2)

- [x] 2.1 Add `tofu/dependabot_dispatch.tf`. It declares the `dependabot-dispatch` environment in troupe and in website
  (main only, no admin bypass, no reviewers), their `main` deployment policies, and
  `DISPATCH_APP_CLIENT_ID` in both from 1.1. Verify `tofu fmt` and `tofu validate` are clean.
- [x] 2.2 Add both environments to `scripts/tests/test_main_only_environments.py` (`TF_FILES` and `MAIN_ONLY`). Verify
  the test passes, and fails when either declaration is deleted, widened beyond `main`, or opened to an admin bypass.
- [x] 2.3 Declare the App in `oob/app-installations.json`, and its repository in the hand-confirmed list. Add "The
  dispatch App (set up by hand)" to `oob/README.md`: creating it, and setting `DISPATCH_APP_PRIVATE_KEY` in both
  environments with a command that prints nothing and checks the key's first line (PKCS#1). Add a row to README.md's
  table for `tofu/dependabot_dispatch.tf`. Verify the oob tests pass, and that the drift check, run locally, reports no
  difference for the App.

## 3. The backstop in the script (spec dependency-updates: backstop, missed event, tracking issue; design D4, D5)

- [x] 3.1 Add `--backstop` to `scripts/dependabot_issues.py`. When it's given, count as a miss each open Dependabot
  pull request that needs a new or relinked issue, or its closing line, and whose `updated_at` is over the hour (one
  named constant). Without it, behave as now. Test it with fixtures based on real payloads: a miss for a missing line
  and for a missing issue; no miss within the hour; no miss for closing merged or not-planned issues or reopening; and
  no miss without `--backstop`. Verify the tests pass, with `GITHUB_ACTIONS` set both ways.
- [x] 3.2 Keep the "Dependabot events missed" tracking issue in infrastructure. Open it when there are misses and none
  is open, comment only when the set differs from the last report, and close it clean with a comment linking the run.
  Ignore same-titled issues by anyone else, and update the oldest when two are open. The issue gets no `dependencies`
  label and no update marker. Test each case, and that the script's update listing never takes the tracking issue for
  an update's issue. Verify the tests pass.
- [x] 3.3 Make every write first, then report the misses and exit 1. Add the tracking issue's URL to the
  `issue-urls` output. Test that the exit code and message name the misses and any failed repository together, and
  that outside Actions the backstop only prints what it would open, comment or close. Verify the tests pass, and that
  a local `uv run scripts/dependabot_issues.py --backstop` only reads.

## 4. The workflows (spec dependency-updates: Dependabot's runs, dispatch, workflow never runs code; design D1–D3, D7)

- [x] 4.1 In `.github/workflows/dependabot-issues.yml`, replace the `*/10` cron with `workflow_run` of "Dependabot
  Updates" (`completed`), a daily `37 4 * * *`, and `workflow_dispatch` with a boolean `backstop` input. Pass
  `--backstop` on `schedule` or when the input is set. Update the header comment and the concurrency comment (D3). Extend
  `scripts/tests/test_dependabot_issues_workflow.py`: the triggers, the single daily cron, no expression reading
  `github.event.`, the backstop flag's condition, and the existing checkout pin. Verify the tests pass.
- [x] 4.2 Add `.github/workflows/dependabot-dispatch.yml` (D2). It runs on `workflow_run` of "Dependabot Updates" with
  `permissions: {}`. Its one job is skipped in `troupe-run/infrastructure`, uses the `dependabot-dispatch`
  environment, mints the dispatch token for `repositories: infrastructure` with `permission-actions: write`, and runs
  `gh workflow run dependabot-issues.yml -R troupe-run/infrastructure --ref main`. It has the delivered-file header.
  Add `scripts/tests/test_dependabot_dispatch_workflow.py` to check: no checkout, no `github.event.` expression, the
  repository condition, the environment, the token's scope, and the one dispatch command. Verify the tests pass and
  `actionlint` is clean, if `scripts/check.py` runs it.
- [x] 4.3 Add the dispatcher to `guard_files` in `tofu/guard_delivery.tf`, and run `uv run scripts/dependabot_config.py`.
  Verify `tofu/dependabot/troupe.yml` and `website.yml` now leave out `.github/workflows/dependabot-dispatch.yml`,
  infrastructure's leaves out nothing, and the guard-delivery and Dependabot config tests pass.

## 5. Watching the backstop (spec schedule-watch; design D6)

- [ ] 5.1 Add `{"repository": "infrastructure", "workflow": "dependabot-issues.yml", "max_age_days": 2}` to
  `scripts/watched-schedules.json`, and update the test that names the declared entries. Verify
  `test_watch_schedules.py` passes, and that a local `uv run scripts/watch_schedules.py` reads the new entry. Before
  the first scheduled run it reports that the workflow has never run on its schedule, which is expected until the
  merge.

## 6. Docs (design D1–D6)

- [ ] 6.1 Update "Dependabot pull requests" in `docs/development-workflow.md`. Say what starts the run: Dependabot's
  runs, the dispatch from troupe and website, the daily backstop, and by hand. Give the hour bound, and say that a
  missed event shows in the "Dependabot events missed" issue. Say that closing a Dependabot pull request by hand closes
  its issue at the next backstop. Update README.md's rows for `dependabot-issues.yml` and the delivered workflows.
  Verify `uv run scripts/check.py` passes, the docs build included, if it checks docs.

## 7. Checks and the pull request (Migration 3)

- [ ] 7.1 Run `uv run scripts/check.py` and a local plan, fast-forwarded onto `origin/main`. Verify the check passes,
  and the plan shows the two environments, their policies, the two variables, the dispatcher and the new
  `guard-delivery.json` delivered to troupe and website, and the regenerated `dependabot.yml`s, and nothing else.
- [ ] 7.2 Open the pull request with `Closes #195`, its body written to a file first and passed to `--body-file`.
  Verify CI is green on all three OSes and the plan comment matches 7.1.

## Workflow follow-up

- Archive the change on the branch, batched with the rebase onto `main`'s state commit, and ask for the plan approval
  once.
- After the merge and the apply, the owner sets `DISPATCH_APP_PRIVATE_KEY` in troupe's and website's
  `dependabot-dispatch` environments (oob/README.md).
- Check end to end (design Migration 5). Comment `@dependabot rebase` on a Dependabot pull request that's behind
  `main` in each repository, and see `dependabot-issues` start and restore the line within the hour. Run the backstop
  by hand with `backstop` set and see it succeed with no tracking issue. Then confirm the first scheduled run, and the
  watch's clean report.
- Comment on #195 with the PR and the archived change, check it's closed and its card says Done, and remove the
  by-hand step from the `dependabot-issues-findings` memory.
