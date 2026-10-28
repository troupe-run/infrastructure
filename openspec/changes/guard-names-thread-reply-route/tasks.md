# Tasks

Each group is its own commit, saying `Part of #210`, never a closing keyword: a commit message's `closes #n` closes the
issue when it reaches `main`. The pull request closes #210.

## 1. A refused reply names the allowed reply (design D1, D2, D3)

- [x] 1.1 Write the tests first in `scripts/tests/test_guard_review_threads.py`: extend
  `test_the_other_ways_to_reply_are_refused` so the `addPullRequestReviewThreadReply` refusal's fix names
  `gh api -X POST repos/<owner>/<repo>/pulls/<n>/comments -F in_reply_to=<comment id>`, the
  `.../comments/3012345678/replies` refusal's fix names
  `gh api -X POST repos/troupe-run/infrastructure/pulls/7/comments -F in_reply_to=3012345678`, and neither fix says
  "add it to the list". Verify both fail on the current guard
- [x] 1.2 Write the tests first in `scripts/tests/test_guard_gh.py`: the `addLabelsToLabelable` refusal's fix doesn't say
  "add it to the list"; one document with `addComment` and `deleteIssue` names `gh issue comment <n>` and ends asking
  the owner for `deleteIssue` only; and every command in `GH_MUTATION_EQUIVALENTS` and `GH_API_EQUIVALENTS`, with its
  `<...>` placeholders filled in (`troupe-run/troupe` for owner and repo, `1` for the rest), is allowed by
  `gh_decision`. Verify the first two fail on the current guard (the third errors until `GH_API_EQUIVALENTS` exists)
- [x] 1.3 In `scripts/guard.py`, add the reply entry to `GH_MUTATION_EQUIVALENTS` and widen its comment (D1); add
  `GH_API_EQUIVALENTS` with the replies endpoint and use it in `gh_decision`'s unlisted-endpoint refusal (D2); end
  `_not_listed_mutations`' fix with the hints alone when every mutation has one, and name only those without one in
  the "ask the owner" tail otherwise (D3). Verify the 1.1 and 1.2 tests and the rest of `test_guard_gh.py` and
  `test_guard_review_threads.py` pass, and `grep -rn "add it to the list" scripts docs` finds no other text that
  quotes the old tail (`scripts/tests/fixtures/plan-pr96.txt` is an old plan, left as it is)
- [x] 1.4 Update `docs/development-workflow.md`'s "Replying in a conversation" to say the refusal of the other two ways
  names the allowed command, and the fix column of its `gh-allow-list` row, which quotes the old tail, to say a refused
  mutation or endpoint with an allowed way names it (now a `gh` command or the reply's `gh api` call), and only the
  rest ask the owner (D3). Verify `uv run scripts/check.py` passes, then commit `fix(guard): …` with `Part of #210`

## 2. A thread id the shell fills in is refused for what it is (design D4)

- [x] 2.1 Write the test first in `scripts/tests/test_guard_review_threads.py`, parametrized over `threadId: "$TID"` in
  a double-quoted query, `threadId: $id` with `-f id=$TID`, and `-F id="$(cat f)"`: the resolve is refused under
  `gh-allow-list`, the fix says to write the id out and doesn't mention gh's login, and the `lookup` fixture records no
  call. Verify it fails on the current guard (the refusal says "couldn't be read" and a lookup is made)
- [x] 2.2 In `review_resolve_decision`, refuse an id `SHELL_EXPANSION` matches before calling `read_review_thread`.
  Verify the 2.1 test and every existing test in `test_guard_review_threads.py` pass
- [x] 2.3 Add to "Resolving a nit" in `docs/development-workflow.md` that the id is written out in the command, since a
  shell variable's value can't be read before it runs. Verify `uv run scripts/check.py` passes (mypy `--strict`, ruff,
  the full suite with `GITHUB_ACTIONS` set and unset), then commit with `Part of #210`

## 3. Pull request and delivery plan

- [x] 3.1 Validate with `openspec validate guard-names-thread-reply-route --strict`, push the branch and open one pull
  request whose description closes #210 (body written to a file, passed with `--body-file`). Verify this repository's
  `guard` run on the pull request passes, and the plan comment changes only `scripts/guard.py`, in troupe and in
  website. Record the PR, the run and the plan here. Result: PR #212. On 93cd523 both `guard` runs pass, as do every
  other check, the guard tests on all three OSes and Claude's review ("no new findings"). The plan for 93cd523 (run
  40680839210) is 0 to add, 2 to change, 0 to destroy: `github_repository_file.guard` for `scripts/guard.py` in troupe
  and in website, content and commit message in place, with no modes to set

## Workflow follow-up

- Act on Claude's review of the last push, then archive on the branch and rebase onto `main`'s state commit before
  asking for the plan's approval, so it's asked once.
- After the owner merges and approves the delivery's apply, check troupe's and website's `scripts/guard.py` match
  `main`'s.
- Check #210 is closed, comment on it with the PR and the archived change, and set its card to Done.
