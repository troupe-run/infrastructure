# Tasks

## 1. The App reads alerts

- [x] 1.1 Add `"vulnerability_alerts": "read"` to `troupe-run-dependabot`'s permissions in `oob/app-installations.json`
      (design D2), and the App's paragraph in `oob/README.md` (which lists its permissions). Verify
      `uv run scripts/check.py` passes and `git diff` shows only that permission and its sentence
- [x] 1.2 Owner (ask with AskUserQuestion, don't tick without the answer): add "Dependabot alerts: read" to the App
      and accept it on the org's installation. Verify with
      `gh api orgs/troupe-run/installations --jq '.installations[] | select(.app_slug=="troupe-run-dependabot") | .permissions'`
      that it shows exactly issues write, metadata read, pull_requests write and vulnerability_alerts read, and
      `uv run scripts/oob.py` reports nothing for App installations on this branch
- [x] 1.3 With the owner's login, read website's alerts with
      `gh api 'repos/troupe-run/website/dependabot/alerts?state=open&per_page=100'` and save a trimmed copy (number,
      state, ecosystem, package, manifest path, first patched version) as a test fixture under
      `scripts/tests/fixtures/`. Verify it holds website's open zod, fast-uri and postcss-selector-parser alerts and
      a fixed undici one

## 2. Dependabot issues: a milestone for security updates only

- [x] 2.1 Write the tests first, in `scripts/tests/test_dependabot_issues.py`, from the spec's scenarios
      (dependency-updates: "A security update is told by the repository's open alerts", "A run that can't read a
      repository's alerts opens no issue there", "A run never takes a milestone off an issue", and the modified
      "Every Dependabot pull request has its issue"), using 1.3's fixture and website's real pull request titles and
      branches (#44 zod, #46 fast-uri, #54 postcss-selector-parser, #55 typescript). Include a `uv-build` /
      `uv_build` name match and an unmapped ecosystem. Verify they fail on this branch before 2.2, for the reason
      each one names
- [x] 2.2 Implement design D1 and D3 in `scripts/dependabot_issues.py`: the ecosystem map, name normalisation,
      reading the open alerts in `read_repository` (all pages, only when there's a Dependabot pull request, a
      failure being a `ReadError`), a `security` flag per pull request carried on `Action`, the milestone only on a
      security update's `open`, set on `relink` only when the issue has none, and `describe` saying which. Update
      the module docstring. Verify 2.1's tests pass, the existing tests still pass, and
      `uv run scripts/check.py` passes (mypy --strict, ruff)
- [x] 2.3 Check that no existing test or scenario still expects a version update's issue to get a milestone:
      `grep -n "milestone" scripts/tests/test_dependabot_issues.py`, and read each hit. Verify each one now says
      security update, or asserts no milestone
- [x] 2.4 Run `uv run scripts/dependabot_issues.py` locally (it only reads, design D8 of dependabot-issues) and verify
      its output matches today's state: website's open Dependabot pull requests, if any, each say "security update"
      or not, as the alerts say. Keep the output for the pull request
- [x] 2.5 Update `docs/development-workflow.md`'s "Dependabot pull requests": only a security update's issue gets the
      release in progress, told by the repository's open alerts, and a version update's gets none; a run that can't
      read the alerts opens no issue in that repository. Verify `uv run scripts/check.py` passes (the docs gates)

## 3. The list on a milestone-closing plan

- [x] 3.1 Write `scripts/tests/test_milestone_review.py` first, from the milestones spec's two ADDED requirements:
      a plan closing `0.1.0` in four repositories lists it once; a plan re-describing a milestone, or with no
      milestone change, writes an empty file; `.github` with issues off is left out and said so; pull requests are
      dropped; a second page is read; a failed read exits non-zero naming the repository and writes no list; a title
      with Markdown markup is escaped. Use a `plan.json` fixture with `github_repository_milestone.release` changes
      shaped like `tofu show -json`'s, and a stubbed `gh`. Verify they fail before 3.2
- [x] 3.2 Write `scripts/milestone_review.py` (design D4), in the style of `plan_checks.py` and `hook_modes.py`:
      standard library, `gh api` for reads, a docstring citing the spec and design. Verify 3.1's tests pass and
      `uv run scripts/check.py` passes
- [x] 3.3 Add a "Issues with no milestone" step to both plan jobs in `.github/workflows/tofu.yml`, after "Check
      warnings" and before the comment or summary step, with `GH_TOKEN: ${{ github.token }}`, and `cat` its file
      into the head of "Post the plan on the pull request" and "Show the plan for approval". No job permission
      changes. Verify the workflow tests (`uv run pytest scripts/tests -k workflow`) and `uv run scripts/check.py`
      pass, and `git diff .github/workflows/tofu.yml` shows no new permission
- [x] 3.4 Probe it on the real repositories: run `uv run scripts/milestone_review.py` locally with a `plan.json` that
      closes `0.1.0` (3.1's fixture) and the owner's `gh` login. Verify its section lists the open issues with no
      milestone that `gh api 'repos/troupe-run/<repo>/issues?milestone=none&state=open' --paginate` gives for
      troupe, infrastructure and website, without pull requests, and leaves `.github` out. Keep the output for the
      pull request: it's #229's "a test or probe shows the list"

## 4. The rule in the docs

- [x] 4.1 Rewrite `org-profile/CONTRIBUTING.md`'s "Milestones" section and the follow-up sentence in "How issues are
      related" (design D6; org-profile spec, modified and added requirements): the "would that release wait for it?"
      rule, no milestone for everything else open or closed, follow-ups, Decisions unchanged, and the release review
      with its three outcomes and the list on the closing pull request. Remove "Completed work always has a
      milestone". Verify `uv run scripts/check.py` passes (org-profile tests, links, issue types), and
      `grep -n "always has a milestone" org-profile/CONTRIBUTING.md` finds nothing
- [x] 4.2 In `docs/standard-changes.md`, say the sub-issue takes the needing issue's milestone because the needing
      issue waits for it (it's blocked by the sub-issue). Leave the commands and checklist steps as they are. Verify
      `git diff docs/standard-changes.md` changes wording only, and `uv run scripts/check.py` passes
- [x] 4.3 Search for anything else that states the old rule:
      `grep -rn -i "release in progress\|always has a milestone\|when it was done" --include=*.md --include=*.py . | grep -v openspec/changes/archive`.
      Verify each hit agrees with the new rule, or fix it

## 5. Verify

- [x] 5.1 Run `openspec validate needed-for-milestones --strict` and verify it passes
- [x] 5.2 Fast-forward onto `origin/main`, run `uv run scripts/check.py` and `uv run scripts/oob.py`, and verify both
      are clean (the App's permission matches after 1.2)
- [x] 5.3 Once the owner approves the pull request's first `plan-pr` run, read its plan comment and verify the plan
      shows only `.github`'s `CONTRIBUTING.md` updated in place, and no "Issues with no milestone" section (this
      pull request closes no milestone). Tick it in the same push as the archive, so the owner approves one more run (plan for 35787e4, run 41145490021: 0 to add, 1 to change, 0 to destroy, `CONTRIBUTING.md` only; no list; the step logged "84 milestone changes, none closes a milestone", 4 repositories × 21 milestones, so it reads the real plan shape)

## Workflow follow-up

- Open the pull request with `Closes #229`, 2.4's dry run and 3.4's probe output. Before the second `plan-pr` approval,
  archive the change and rebase onto `main`'s state commit in one push.
- The owner merges by rebase, through the merge queue, then approves the `plan (main)` apply that delivers
  `CONTRIBUTING.md`.
- After the merge: comment on #229 with the pull request and the archived change, check it's closed and its card is
  Done, and tell #230 it can start.
