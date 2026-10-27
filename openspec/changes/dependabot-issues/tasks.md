# Tasks

## 1. The App, and what GitHub allows it (design D7, Migration 1–2)

- [ ] 1.1 Ask the owner to create `troupe-run-dependabot` with Issues read/write, Pull requests read/write and
  Metadata read, no organisation permission and no webhook, and to install it on troupe, website, infrastructure and
  `troupe-run/infra-probe-dependabot-issues`. Verify with the owner's org App list that the installation exists, and
  record the App's ID and client ID on #172.
- [ ] 1.2 Create `troupe-run/infra-probe-dependabot-issues` with an `npm` manifest pinning an old patch release, a
  `.github/dependabot.yml` for it, and a workflow on `pull_request: [edited]` that only echoes. Verify Dependabot
  opens a pull request there (`gh pr list -R troupe-run/infra-probe-dependabot-issues --author app/dependabot`).
- [ ] 1.3 With an App token, in the probe repository: create an issue with `type: Task`, a label and a milestone; edit
  the Dependabot pull request's description to add `Closes #<n>`; then comment `@dependabot rebase`. Verify and record
  in design.md (Risks):
  - the issue's type is Task (`gh api repos/.../issues/<n> -q .type.name`), or what permission it needed;
  - the edit started the `edited` workflow (`gh run list`);
  - whether the closing line survived the rebase.
- [ ] 1.4 Remove the probe repository from the App's installation and delete it. Verify
  `gh repo view troupe-run/infra-probe-dependabot-issues` fails.

## 2. The credential declarations (spec dependabot-issue-credentials)

- [ ] 2.1 Add `tofu/dependabot_issues.tf`: the `dependabot-issues` environment in infrastructure (main only, no admin
  bypass, no reviewers), its `main` deployment policy, and `DEPENDABOT_APP_CLIENT_ID` from 1.1. Verify `tofu fmt` and
  `tofu validate` are clean.
- [ ] 2.2 Add the environment to `scripts/tests/test_main_only_environments.py`. Verify the test passes, and fails
  when the declaration is deleted, widened beyond `main`, or opened to an admin bypass.
- [ ] 2.3 Declare the App in `oob/app-installations.json`, and document creating it and setting its key in
  `oob/README.md`, with a command that prints nothing and checks the key's first line (PKCS#1). Verify the oob tests
  pass and the drift check, run locally, reports no difference for the App.

## 3. The script (spec dependency-updates; design D2–D6, D8)

- [x] 3.1 Save real payloads as fixtures under `scripts/tests/fixtures/dependabot-issues/`: website #44 (patch), #55
  (major), #58 (scoped name), #54 (`build(deps):`), troupe #175 (requirement range) and infrastructure #184
  (`github-actions`), with a README saying where each came from. Verify each fixture's fields match
  `gh api repos/troupe-run/<repo>/pulls/<n>`.
- [x] 3.2 Write the title parser, the dependency key and the update type in `scripts/dependabot_issues.py` (D3, D4).
  Test each fixture's dependency, directory, versions and type, an unparseable title, and that `0.30.0 → 0.30.2` is
  patch and `3 → 7` is major. Verify the tests pass.
- [x] 3.3 Add choosing the release in progress (D5). Test today's `tofu/milestones.json` gives `0.1.0`, a declaration
  with no open milestone fails before any write, and a repository missing the title fails alone. Verify they pass.
- [x] 3.4 Add reading a repository and planning its writes (D2, D6): new issue, relink, reopen, restore the line,
  close as completed, close as not planned after the hour, and nothing to do. Use a fake `gh`. Test each spec scenario
  of "Every Dependabot pull request has its issue", "closes its issue", "superseded", "closed without merging" and
  "only … trusted", including a person's `dependabot/...` branch, a person's issue with a copied marker, and a
  closing line to another issue. Verify they pass.
- [x] 3.5 Add the writes, through `gh api` with the fields as JSON on stdin (a description can exceed an
  argument's size limit), and the read-only mode outside Actions (D8). Test a run with `GITHUB_ACTIONS` unset makes no write and prints each, and with it `true` makes exactly the planned
  writes. Test a repository whose listing fails is left alone while the others are handled, and the run exits 1
  naming it. Verify the tests pass both with and without `GITHUB_ACTIONS=true`, and that mypy `--strict` and ruff are
  clean.
- [x] 3.6 Run the script locally against the live repositories. Verify it prints an issue it would open for each of
  the 18 open Dependabot pull requests (or however many are open then), and writes nothing.

## 4. The workflow (design D1, D6, D7)

- [x] 4.1 Write `.github/workflows/dependabot-issues.yml`: `schedule` every 10 minutes and `workflow_dispatch`;
  `concurrency` without cancelling; an `issues` job in the `dependabot-issues` environment that mints the App's token
  for the three repositories and runs the script; a `board` job in the `board` environment that checks each issue URL
  against `^https://github\.com/troupe-run/(troupe|website|infrastructure)/issues/[0-9]+$` and adds those missing from
  the board. Verify `scripts/check.py` passes.
- [x] 4.2 Add `scripts/tests/test_dependabot_issues_workflow.py`: no `pull_request` or `pull_request_target`
  trigger, one checkout with no `ref` or `repository`, no `${{ }}` expression reading `github.event`, top-level
  `permissions: {}`, each job's environment, and `cancel-in-progress: false`. Verify it passes, and fails when a
  checkout gains `ref: ${{ github.event.pull_request.head.sha }}`.

## 5. Documentation

- [ ] 5.1 Rewrite the "Dependabot pull requests" section of `docs/development-workflow.md`: each pull request gets its
  issue and closing line from `dependabot-issues`; the update type; majors need an OpenSpec change; what's left until
  #174. Verify `scripts/check.py`'s doc checks pass and the section names the workflow and the issue's contents.

## 6. Plan (Migration 3)

- [ ] 6.1 Run `uv run scripts/check.py`, open the pull request (`Closes #172`), and check its plan shows only the
  environment, its deployment policy and the variable. Record the plan's summary here.

## Workflow follow-up

After the merge (Migration 4–5); these can't be ticked before the archive.

- After the owner-approved apply, ask the owner to set `DEPENDABOT_APP_PRIVATE_KEY` (oob/README.md). Check
  `gh secret list -R troupe-run/infrastructure --env dependabot-issues` lists it by name.
- Start the workflow by hand (`gh workflow run dependabot-issues.yml`). Check website #44, #45 and #46 each have an
  issue of type Task, labelled `dependencies`, in `0.1.0`, on the board (`gh issue view <n> --json projectItems`), and
  a closing line, and that `guard` re-ran on each with `pr-closes-issue` passing. Check the other open Dependabot pull
  requests the same way. Record the issue numbers on #172.
- Check a scheduled run starts on its own within 30 minutes and changes nothing (`gh run list --workflow
  dependabot-issues.yml`, and its log).
- When Dependabot next supersedes one of these pull requests, check its issue was relinked rather than a second one
  opened, and record it on #172.
- Archive the change on the branch before merging; after the merge, comment on #172 with the pull request and the
  archived change, and check its card is Done.
