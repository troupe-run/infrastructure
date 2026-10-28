# Tasks

Each fix is its own commit, saying `Part of #n`, never a closing keyword: a commit message's `closes #n` closes the
issue when it reaches `main`. The pull request closes all three.

## 1. #204: a workflow line that begins with `--` counts (design D1)

- [x] 1.1 Write the test first in `scripts/tests/test_guard_dependabot.py`: on a workflow whose base starts with a
  `---` line, a Dependabot commit that bumps its `uses:` line and removes the `---` is refused under
  `commit-branch-change`, naming the workflow; parametrized also for removing a column-0 `--force` line and adding a
  `++` line. Verify it fails on the current `_only_uses_lines` (the branch passes as exempt)
- [x] 1.2 Make `_only_uses_lines` keep `+`/`-` lines only inside a hunk (after `@@`, before the next `diff --git`).
  Verify the 1.1 test and the existing action-bump and `run:`-line tests pass
- [x] 1.3 Update `docs/development-workflow.md`'s `commit-branch-change` row and "Dependabot pull requests" section to
  say every added and removed workflow line counts, whatever it begins with. Verify `uv run scripts/check.py` passes,
  then commit `fix(guard): …` with `Part of #204`

## 2. #205: a merge commit isn't exempt (design D2)

- [ ] 2.1 Write the test first: on `dependabot/npm_and_yarn/x` in `troupe-run/website`, a patch update of
  `package-lock.json`, then a `--no-ff` merge of a side Dependabot commit whose merge also changes `src/index.ts`,
  committed with a Dependabot patch-update subject, is refused under `commit-branch-change`, and the refusal names the
  merge commit's short sha and says it's a merge commit. Verify it fails on the current guard (the branch passes)
- [ ] 2.2 Make `dependabot_ineligibility` read each commit's parents with its message and add D2's reason for any
  commit with more than one parent. Verify the 2.1 test and the rest of `test_guard_dependabot.py` pass
- [ ] 2.3 Add the merge commit to the docs' list of what isn't exempt (the `commit-branch-change` row and "Anything
  else takes an OpenSpec change"). Verify `uv run scripts/check.py` passes, then commit with `Part of #205`

## 3. #206: the labels' token isn't re-sent on a redirect (design D3)

- [ ] 3.1 Write the test first in `scripts/tests/test_guard_capability_labels.py`: with `GITHUB_TOKEN` set, a `send`
  stub that passes the request to `urllib.request.HTTPRedirectHandler().redirect_request` with a 302 to
  `https://elsewhere.example/` records a redirected request with no `Authorization` header. Verify it fails on the
  current `declared_labels` (the header is carried)
- [ ] 3.2 Add the header with `add_unredirected_header`. Verify the 3.1 test and
  `test_the_run_s_token_is_sent_when_there_is_one` pass
- [ ] 3.3 Say in the docs' `capability-label` row that the token is sent only to GitHub's API, never on to a
  redirect. Verify `uv run scripts/check.py` passes (mypy `--strict`, ruff, the full suite with `GITHUB_ACTIONS` set
  and unset), then commit with `Part of #206`

## 4. Pull request and delivery plan

- [ ] 4.1 Validate with `openspec validate guard-fixes --strict`, push the branch and open one pull request whose
  description closes #204, #205 and #206 (body written to a file, passed with `--body-file`). Verify this
  repository's `guard` run on the pull request passes, and the plan comment changes only `scripts/guard.py`, in troupe
  and in website. Record the PR, the run and the plan here
- [ ] 4.2 Before asking for the plan's approval, list the open Dependabot pull requests in troupe, infrastructure and
  website, and check each for a merge commit or a workflow line beginning `--` or `++` that it changes. Record the
  list and the result here; if any would go red, raise it with the owner

## Workflow follow-up

- Act on Claude's review of the last push, then archive on the branch and rebase onto `main`'s state commit before
  asking for the plan's approval, so it's asked once.
- After the owner merges and approves the delivery's apply, check troupe's and website's `scripts/guard.py` match
  `main`'s.
- Check #204, #205 and #206 are closed, comment on each with the PR and the archived change, and set their cards to
  Done. #194 stays open unless its owner says otherwise.
