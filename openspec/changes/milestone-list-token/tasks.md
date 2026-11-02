# Tasks

## 1. Probe GitHub's behaviour, and the App's permission (design Context, D1)

- [x] 1.1 Create public `troupe-run/infra-probe-milestone-list` with one open issue (no milestone) and one open pull
  request, and a workflow that prints `open_issues_count` and the open items `issues?state=open` lists (with and
  without `milestone=none`) for itself, troupe, website and infrastructure, from a `contents: read` job and a job
  with `pr-plan`'s permissions. Done: the `contents: read` job saw everything; the `pull-requests: write` job saw only
  pull requests (troupe 10 of 67). The finding went to the owner, who chose D1
- [x] 1.2 Record 1.1's results in a comment on #247, then delete the repository and verify `gh repo view` reports
  it gone
- [ ] 1.3 Declare `"pull_requests": "read"` for `troupe-run-infrastructure` in `oob/app-installations.json`. The owner
  grants "Pull requests: Read-only" in the App's settings and accepts it on the org's installation. Verify
  `gh api orgs/troupe-run/installations` shows the permission, and `uv run scripts/oob.py` reports no installation
  difference

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
  derived from `tofu/milestones.json`, and `permission-issues: read` and `permission-pull-requests: read` as its only `permission-*` inputs; the list step's
  `GH_TOKEN` is that step's output; the jobs' permissions are unchanged. Rename the test that says "the job's own
  token". Verify the new tests fail on the current workflow
- [ ] 3.2 Add the token step to `pr-plan` and `plan` in `.github/workflows/tofu.yml`, pointing each list step's
  `GH_TOKEN` at it, and rewrite the comment above `pr-plan`'s step to say which token reads and why (#247). Verify
  `uv run scripts/check.py` passes, including the workflow tests and actionlint if the check runs it
- [ ] 3.3 Prove the token D1 mints sees every issue: mint one locally for the four repositories with the permissions
  3.1 pins (JWT from the App's key in 1Password, then `app/installations/<id>/access_tokens`; the owner runs any `op`
  prompt; never print the key or token), and run the script with it against a scratch
  `tofu show -json` with one milestone's state edited to `closed`. Verify it lists troupe's open issues with no
  milestone, matching a run with the owner's `gh` login, and passes the count check. Never print the key or token;
  delete the scratch files afterwards

## Workflow follow-up

- The PR's own plan closes no milestone, so CI can't show the list. Its evidence is 1.x, 3.3 and the tests. The next
  milestone-closing PR's plan comment is the first run in CI: compare it with a local run once.
- After the merge, update the `milestone-review-list-reads-none` memory: the local workaround is no longer needed.
- Archive on the branch before merging; after the merge, comment on #247 with the PR and the archived change, and
  check the board card is Done.
