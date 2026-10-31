# Tasks

## 1. The token asks for what the App is declared with

- [x] 1.1 Write the test first, in `scripts/tests/test_dependabot_issues_workflow.py` (design D2, D3; spec: "The
      workflow's token asks for the App's declared permissions"): read `troupe-run-dependabot`'s entry from
      `oob/app-installations.json`, drop `metadata`, turn each key into its input name (`_` → `-`, prefixed
      `permission-`) with its level, and pass that as the `issues` token's `granted`. Fail, naming the App, if the
      entry is missing or has no permissions. Make `token_problems`'s message name each permission missing from the
      token and each one the token asks for beyond the declaration. Add mutation cases: removing
      `permission-vulnerability-alerts` from a copy of the workflow, and adding `permission-contents: read`, each
      fail naming that permission; and one that adds a permission to a copy of the declaration fails naming it.
      Verify `uv run pytest scripts/tests/test_dependabot_issues_workflow.py` fails on this branch before 1.2, naming
      `permission-vulnerability-alerts` as declared but not asked for, and for no other reason
- [x] 1.2 Add `permission-vulnerability-alerts: read` to the `issues` job's "Mint the troupe-run-dependabot App's
      token" step in `.github/workflows/dependabot-issues.yml` (design D1), and say in the step's comment that the token
      asks for the App's declared permissions, checked against `oob/app-installations.json`. Verify 1.1's tests pass,
      `uv run scripts/check.py` passes, and `git diff .github/workflows/dependabot-issues.yml` adds that one input and
      the comment, and no job permission
- [x] 1.3 In `oob/README.md`'s `troupe-run-dependabot` paragraph (line ~238, which lists its permissions), add that the
      `dependabot-issues` token asks for each of them and `scripts/check.py` holds the two together, so a permission
      added here needs the workflow too. Verify `uv run scripts/check.py` passes (the docs gates) and `git diff
      oob/README.md` is that sentence only

## Workflow follow-up

- Open the pull request as a draft with `Closes #238`, act on Claude's review of the last push, then mark it ready.
- Archive the change on the branch before merging; the owner merges by rebase through the merge queue.
- After the merge, verify on `main` (design D4; it can't run before, since the `dependabot-issues` environment deploys
  only from `main`). Ask the owner with AskUserQuestion whether to start a run
  (`gh workflow run dependabot-issues -R troupe-run/infrastructure --ref main`) or wait for the daily schedule. From
  that run's log (`gh run view <id> --log`), check the issues job passes and reports website with no 403 (expected
  `troupe-run/website: nothing to do`, since #55 is typescript, which has no open alert). If it fails, stop and raise
  it with the owner before treating #238 as done (design, Risks).
- Then comment on #238 with the pull request, the archived change and the run, and check
  #238 is closed and its card on the troupe roadmap board says Done.
