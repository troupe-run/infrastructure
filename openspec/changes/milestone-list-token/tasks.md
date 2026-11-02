# Tasks

## 1. Probe GitHub's behaviour (design D3)

- [ ] 1.1 Create public `troupe-run/infra-probe-milestone-list` with one open issue (no milestone) and one open pull
  request, and a workflow (`permissions: contents: read`) that prints `open_issues_count` and the length of
  `issues?state=open` for itself and for `troupe-run/website`. Verify from the run log that each list holds only the
  pull requests while the count includes the issues. If either doesn't hold, stop and bring the finding to the owner
  before 2.x
- [ ] 1.2 Record 1.1's results in a comment on #247, then delete the repository and verify `gh repo view` reports
  it gone

- [ ] 1.3 Test design D2's precondition: mint an issues-only token from the infrastructure App locally (JWT from the
  App's key in 1Password, then `app/installations/<id>/access_tokens` with `{"permissions":{"issues":"read"}}`; the
  owner runs any `op` prompt; never print the key or token), and compare `issues?state=open` for troupe with the
  owner's `gh` login. Record on #247 whether the pull requests are listed. If they aren't, stop and ask the owner to
  choose between `pull_requests: read` on the App and the search count, record the choice in design D2, and adjust
  2.x and 3.x before going on

## 2. The script refuses a short read (design D2)

- [ ] 2.1 Write the failing tests first in `scripts/tests/test_milestone_review.py`: a repository whose read holds
  fewer open items than its `open_issues_count` fails with exit 1, names the repository and both numbers, and writes
  no list; one whose read matches lists its issues with no milestone as before; issues with a milestone and pull
  requests are left out of the list. Verify they fail on the current script
- [ ] 2.2 Change `unmilestoned` to read `issues?state=open&per_page=100`, all pages, check the count against
  `open_issues_count` (an absent or non-integer count is a read error), and keep open issues whose `milestone` is
  `null`. Update the existing tests' fakes to the new path. Verify `uv run pytest scripts/tests/test_milestone_review.py`
  passes, and that the existing "can't be read" and "every page" tests still pass unchanged in what they assert
- [ ] 2.3 Update the script's docstring (which token it expects, the count check) and verify `uv run scripts/check.py`
  passes (mypy --strict, ruff)

## 3. The plan jobs read with an App token (design D1)

- [ ] 3.1 Change `scripts/tests/test_milestone_review_workflow.py` first: each job has a "Token to read the issues"
  step before "Issues with no milestone", with the same `if:`, App 5272634, `owner: troupe-run`, the repositories
  derived from `tofu/milestones.json`, and `permission-issues: read` (plus `permission-pull-requests: read` if 1.3 chose it) as its only `permission-*`
  inputs; the list step's
  `GH_TOKEN` is that step's output; the jobs' permissions are unchanged. Rename the test that says "the job's own
  token". Verify the new tests fail on the current workflow
- [ ] 3.2 Add the token step to `pr-plan` and `plan` in `.github/workflows/tofu.yml`, pointing each list step's
  `GH_TOKEN` at it, and rewrite the comment above `pr-plan`'s step to say which token reads and why (#247). Verify
  `uv run scripts/check.py` passes, including the workflow tests and actionlint if the check runs it
- [ ] 3.3 Prove an `issues: read` token from the infrastructure App sees the issues: mint one locally for the four
  repositories with the permissions 3.1 pins, as 1.3 does, and run the script with it against a scratch
  `tofu show -json` with one milestone's state edited to `closed`. Verify it lists troupe's open issues with no
  milestone, matching a run with the owner's `gh` login, and passes the count check. Never print the key or token;
  delete the scratch files afterwards

## Workflow follow-up

- The PR's own plan closes no milestone, so CI can't show the list. Its evidence is 1.x, 3.3 and the tests. The next
  milestone-closing PR's plan comment is the first run in CI: compare it with a local run once.
- After the merge, update the `milestone-review-list-reads-none` memory: the local workaround is no longer needed.
- Archive on the branch before merging; after the merge, comment on #247 with the PR and the archived change, and
  check the board card is Done.
