# Tasks

## 1. The release branch passes the branch rule, narrowly

- [ ] 1.1 Write failing tests in `scripts/tests/test_guard_push_and_ci.py`, each named for what its body checks
      (design D1, D2), with `RELEASE_AUTHOR_EMAIL` patched to a test address and commits authored with
      `git commit --author`: a `release-please--branches--main` branch whose only commit, `chore: release main`, is
      the bot's passes `run_ci`; the same branch with one commit by someone else, alone or after the bot's, fails on
      `commit-branch-change`; a branch with another name and no change, carrying only the bot's commits, fails on
      `commit-branch-change`; the bot's non-conventional commit on the release branch fails on `commit-message` and
      names the commit; a release branch adding no commit fails on `commit-branch-change`; with
      `RELEASE_AUTHOR_EMAIL` left `None`, the bot's release branch fails on `commit-branch-change`; and after `main`
      gains someone else's commit and the release commit is rebuilt on it, a push range from the old head to the
      new one passes. Verify they fail with `uv run pytest scripts/tests/test_guard_push_and_ci.py`
- [ ] 1.2 Add `RELEASE_AUTHOR_EMAIL: str | None = None` next to `DELIVERY_AUTHOR_EMAIL`, with a docstring saying how
      to fill it, and make `run_ci` skip the branch-change rule only for a `release-please--` branch whose commits
      not on `origin/main` are non-empty and all authored by it (design D1, D2). Verify 1.1's tests pass, every
      existing test in `test_guard_push_and_ci.py` and `test_guard_delivery.py` still passes, and
      `uv run scripts/check.py` passes (mypy --strict, ruff)

## 2. Pull request titles are Conventional Commits

- [ ] 2.1 Write failing tests in `scripts/tests/test_guard_push_and_ci.py` (design D3): `run_ci` with the title
      `chore: release main` and conforming commits passes; with `Release main` it returns one `commit-message`
      refusal whose problem names the title and whose fix says to edit the title, not to amend a commit; with no
      title (a push) no title is checked; `github_ci_inputs`, given a `pull_request` event payload file through
      `GITHUB_EVENT_PATH`, returns its `pull_request.title`, and given a payload with no string title, the run fails
      saying it couldn't read the title; `guard.py ci --title 'Release main'` exits 1 and prints the refusal. Verify
      they fail
- [ ] 2.2 Add `pr_title`, the title to `github_ci_inputs` and `run_ci`, and `--title` to `guard.py ci` (design D3).
      Verify 2.1's tests pass, all of `scripts/tests/` passes, and `uv run scripts/check.py` passes

## 3. The check re-runs when a title changes

- [ ] 3.1 Write a failing test in `scripts/tests/test_required_checks.py` that `guard.yml`'s `pull_request` trigger
      has exactly the types `opened`, `edited`, `synchronize` and `reopened`, and that `push` still covers every
      branch. Verify it fails
- [ ] 3.2 Add the types to `.github/workflows/guard.yml` and update its header comment to say titles are checked
      (design D4). Verify 3.1's test passes and `uv run scripts/check.py` passes

## 4. Docs

- [ ] 4.1 Update `docs/development-workflow.md`: the `guard` check row says it checks a pull request's title and
      re-runs on a rename; the `commit-branch-change` row names the release-branch exception and its two conditions;
      the `commit-message` row says a pull request title is checked the same way; Known gaps gains an entry that
      the release exemption trusts the commit's author, and that the hard check is the ruleset declared by #34
      (design D5). Verify `test_guard_docs.py` passes
      and `uv run scripts/check.py` passes

## 5. Evidence

- [ ] 5.1 In a throwaway repository `troupe-run/infra-probe-pr-title` holding this branch's `guard.yml` and
      `scripts/guard.py`, open a pull request titled `Release main` and confirm `guard (workflow rules)` fails naming
      the title; rename it to `chore: release main` with no new commit and confirm the check re-runs and the PR's
      `guard (workflow rules)` shows green. Record the run URLs, then delete the repository and confirm it's gone
- [ ] 5.2 Run `uv run scripts/tofu.py plan` and verify it shows only the delivered `scripts/guard.py` and
      `.github/workflows/guard.yml` changing in troupe; keep it for the pull request
- [ ] 5.3 Run `openspec validate release-please-prs --strict` and verify it passes

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #33`, the probe's run URLs from 5.1 and the plan from
  5.2.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers the guard to troupe.
- After the apply, confirm troupe's `scripts/guard.py` and `.github/workflows/guard.yml` match `main` here, then
  comment on #33 with the pull request and the archived change, and on troupe-run/troupe#23 that D7 has landed.
- Once #34 has created the App **and applied the `release-please--*` ruleset** (design D5), fill
  `RELEASE_AUTHOR_EMAIL` from `GET /users/troupe-run-release%5Bbot%5D` in its own change and deliver it (design D2).
