# Tasks

## 1. Pin what must not change

- [x] 1.1 Before touching `scripts/guard.py`, add tests in `scripts/tests/test_guard_push_and_ci.py` that pass on
  `main`: a push event's `run_ci_entry` checks no description and passes for a conforming range; the local
  `pr_closes_issue` accepts `Closes #22`, `fixes #22`, `Resolves: https://github.com/o/r/issues/22` and
  `Closes troupe-run/infrastructure#173`, and refuses `Bumps the build.`. Verify they pass on `472ee1e`'s guard,
  and record the run here. Result: written in a file of their own, `scripts/tests/test_guard_pr_description.py`,
  which this change's later tests join (the push test stubs OpenSpec, as the capability-label tests do). With
  `scripts/guard.py` unchanged from `472ee1e`: 6 passed

## 2. The description rule (design D1, D2, D4)

- [x] 2.1 Add `pr_description(description: str) -> Decision` beside `pr_title`, using `CLOSING`, refusing under
  `pr-closes-issue` with D2's problem (the empty-description wording for `""`) and fix. Verify with tests: each
  closing form in 1.1 passes; `Bumps the build.` and `""` are refused, each asserting the rule id and the fix text
  (`gh pr edit`, `Closes #22`, `owner/repo#22`); and the test passes the same strings through `pr_closes_issue`'s
  `--body` and asserts both rules agree on every one (one reading, D1). Result: `pr_description(title, description)`, taking the title to name the pull request.
  9 agreement cases (the four closing forms, `Bumps the build.`, `""`, `Related to #22`, `Closes 22`) and the
  pass/refuse tests, all in `test_guard_pr_description.py`, pass
- [x] 2.2 Give `run_ci` a `description: str | None = None` parameter: when not `None`, append `pr_description`'s
  decision, unless `reserved_release_branch(branch, repository)`. Verify with `run_ci` tests for the spec's
  scenarios: no closing line fails, a closing line passes, a cross-repository close passes, troupe's release branch
  with no closing line passes, a fork's (head repository not troupe) and infrastructure's fail on both
  `pr-closes-issue` and `commit-branch-change`, a `dependabot/...` branch fails on both, and `None` checks nothing.
  Replacing the exemption call with `False` must fail the troupe release test. Result: 9 `run_ci` tests pass. With the exemption replaced by `False`,
  `test_troupe_s_release_pull_request_needs_no_closing_line` fails (1 failed, 37 passed); restored, all pass
- [x] 2.3 Add `--description` to the `ci` subcommand beside `--title`, passed through `run_ci_entry` to `run_ci`.
  Verify with a test running `guard.py ci --head … --title … --description 'Bumps the build.'` that exits 1 naming
  `pr-closes-issue`, and without `--description` that it doesn't. Result: run in-process through `guard.main`, as `guard_ci` in
  `test_guard_push_and_ci.py` does: exit 1 with `guard: pr-closes-issue: pull request 'feat: x'`, and 0 without
  `--description`

## 3. Reading the description on GitHub (design D2, D3)

- [x] 3.1 In `github_ci_inputs`, read `pull_request.body` for a `pull_request` event: a string as is, `null` as `""`,
  a missing key or any other type raises `UnreadableDescriptionError` (docstring citing D3). A push returns `None`.
  `run_ci_entry` reports the error under `pr-closes-issue` with the unreadable-title fix's wording. Give the
  existing pull-request payloads in the CI-entry tests a `body` with a closing line, so they keep testing what
  they're named for. Verify with tests: `body: null` fails as an empty description; no `body` key and `body: 3`
  each fail saying the description couldn't be read; a closing `body` passes; and the existing CI-entry tests pass
  unchanged apart from their payloads. Result: the 5 pull-request payloads in `test_guard_push_and_ci.py` gained `"body": "Closes #22"`, and the
  push test's expected inputs a sixth `None`; before that, they failed with `UnreadableDescriptionError`, as D3
  intends. With a missing `body` mapped to `""` instead of raising, the missing-key test fails; restored, the full
  suite passes (14 skipped for no pwsh)
- [x] 3.2 Verify `edited` re-runs the check: a `run_ci_entry` test whose payload is an `edited` action with a body
  that now closes an issue passes, and `test_guard_workflow.py` still asserts `edited` is among the
  `pull_request` types (add the assertion if it isn't there). Update `guard.yml`'s header comment to say the
  description is checked too and `edited` re-runs it for either. Verify `uv run pytest
  scripts/tests/test_guard_workflow.py scripts/tests/test_guard_delivery.py` passes. Result: `test_an_edited_description_that_now_closes_an_issue_passes` passes. The
  `edited` assertion already exists, in `test_required_checks.py`
  (`test_guard_re_runs_when_a_pull_request_is_renamed_and_still_runs_on_every_push`), not `test_guard_workflow.py`,
  so none was added. The header comment says the description is checked too. `test_guard_workflow.py`,
  `test_guard_delivery.py` and `test_required_checks.py`: 40 passed

## 4. Docs

- [x] 4.1 In `docs/development-workflow.md`: the `guard` check's row says it checks a pull request's description
  closes an issue (re-run when edited, release-please's exempt); `pr-closes-issue`'s row says it's also checked on
  GitHub for every pull request, however opened, with the fix `gh pr edit` or editing on GitHub; the "Dependabot
  pull requests" section says their pull requests also fail `pr-closes-issue`. Verify `uv run pytest
  scripts/tests/test_guard_docs.py` passes, and `uv run scripts/check.py` passes. Result: the layer column takes one value
  (`test_guard_docs.py`'s pattern), so the row stays `Claude` and says in its text that the `guard` check applies
  it on GitHub, as `commit-message`'s row does for the title. `test_guard_docs.py`: 3 passed; `scripts/check.py`
  passed in the commit hook

## 5. Integration checks

- [x] 5.1 Probe the branch's guard on a scratch troupe clone (as in the capability-label change), with
  `GITHUB_EVENT_NAME=pull_request`, `GITHUB_REPOSITORY=troupe-run/troupe` and a hand-written event payload: once for
  `release-please--branches--main` with a body closing nothing (passes `pr-closes-issue`), once for a change branch
  with `Bumps the build.` (fails, naming the rule and fix). Record both outputs here. Nothing is pushed. Result: a
  fresh clone of troupe (`main` 63259b9) in the scratchpad, this branch's guard at 13fd22b, hand-written payloads
  with `head.repo.full_name` `troupe-run/troupe`. `release-please--branches--main` (b9d26f8) with release-please's
  usual body: `every rule passes for release-please--branches--main`, exit 0. A scratch branch `probe-closes`
  (one commit proposing a change with `skip_specs`) with `Bumps the build.`: exit 1 with only `guard:
  pr-closes-issue: pull request 'docs(openspec): propose probe-closes' doesn't close an issue: its description has
  no closing line.` and D2's fix. The same branch with `Closes troupe-run/infrastructure#173` added: `every rule
  passes for probe-closes`, exit 0. The clone was deleted; nothing was pushed
- [ ] 5.2 Push the branch and open the pull request with `Closes #173`. Verify this repository's `guard` run on the
  pull request passes with the new rule active (the branch's `guard.py` runs), and that the PR's plan comment
  changes only the delivered `scripts/guard.py` and `.github/workflows/guard.yml`, in troupe and in website.
  Record the PR, the run and the plan
- [ ] 5.3 Just before asking for the plan's approval, list the open pull requests in troupe, infrastructure and
  website and match each description with `CLOSING` (design D5). Fix any that isn't release-please's or
  Dependabot's, or ask the owner which issue it closes. Record the list and what was done here

## Workflow follow-up

- Archive the change on the branch before asking for the plan's approval, and rebase onto `main`'s state commit, so
  the approval is asked once.
- After the owner merges and approves the delivery's apply, verify on troupe and website: the next pull request's
  `guard` run applies the rule, and troupe's release pull request (#89, or its successor) stays green.
- Comment on #173 with the PR and the archived change, check it's closed and its card says Done. #170 stays open for
  its other sections.
