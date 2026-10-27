# Tasks

## 1. Readiness (design D2)

- [x] 1.1 Read `.github/workflows/ci.yml` from website's and troupe's `main` (`gh api
  repos/troupe-run/<repo>/contents/.github/workflows/ci.yml`), and the delivered `guard.yml` from both; verify each
  workflow behind a required check in `tofu/required-checks.json` (`test`; `check`; `guard (workflow rules)`) has a
  `merge_group:` trigger and no `if:`, path filter or `changes` answer that skips or narrows its required job on that
  event. Record what was read in the PR body
- [x] 1.2 Find each repository's most recent CI run on `main` since website#70 and troupe#183 (`gh run list -R
  troupe-run/<repo> --branch main --workflow ci.yml`); verify it passed, so the queue's first run starts from a green
  workflow

## 2. Turn on both queues (design D1)

- [x] 2.1 Set `merge_queue = true` on `repo_website` and `repo_troupe` in `tofu/repositories.tf`, with a comment on
  each saying where its CI runs on merge groups (website#70, troupe#183), and update infrastructure's comment so it no
  longer says the others follow; verify `tofu fmt -check` and `tofu validate`, and that
  `scripts/tests/test_required_checks.py` still passes (`merge_queue_modules()` now reads all three)
- [x] 2.3 Update the merge-queue bullet in `README.md` so it says the queue is on in infrastructure, website and troupe
  (not "infrastructure first, then website and troupe"); verify with `grep -rn -i "then website and troupe\|website
  and troupe follow" README.md tofu/ docs/ CLAUDE.md` returning nothing, and `uv run scripts/check.py` passing

## 3. The product repositories' docs

- [x] 3.1 Open an issue in troupe-run/website and one in troupe-run/troupe, each with `--project "troupe roadmap"`,
  asking for their CLAUDE.md merge step to say pull requests land through the merge queue (`gh pr merge <n>` queues;
  `--admin` skips it and is for emergencies), linking #197; verify each is on the board (`gh issue view <n> -R
  troupe-run/<repo> --json projectItems`) and linked from #197 in a comment

## 4. Pull request

- [ ] 4.1 Open the pull request (`Closes #197`) with the readiness evidence of 1.1 and 1.2; verify every required check
  passes but `plan (pull request)`, which the owner approves once, after the archive (memory: archive before plan
  approval)

## Workflow follow-up

- Archive the change on the branch, rebase onto main's state commit, and ask for the plan approval once. The PR's
  posted plan is the plan evidence: a local plan couldn't run (1Password's prompt failed with the owner away), and the
  owner chose the PR plan instead (2026-10-27). Check it shows only website's and troupe's `protect main` rulesets
  gaining the `merge_queue` block with merge-queue D2's values (`REBASE`, `ALLGREEN`, 5/5/1, 0 minutes, 60 minutes)
  and `allow_auto_merge` turning on for those two repositories, and nothing else, before the owner adds it to
  infrastructure's merge queue.
- After the owner approves the apply of `main`: check that website's and troupe's `protect main` rulesets on GitHub
  have the merge queue rule with `merge_method: REBASE` (`gh api repos/troupe-run/<repo>/rules/branches/main`), and
  that `allow_auto_merge` is true on both (`gh api repos/troupe-run/<repo> --jq .allow_auto_merge`).
- Check that the next pull request in each repository lands through its queue (design D3): its merge group's required
  checks (website `test`, `guard (workflow rules)`; troupe `check`, `guard (workflow rules)`, `DCO`) pass, and `main`'s
  head equals the tested commit. In troupe, check `DCO` on the first queued Dependabot pull request, and that the first
  release-please release after the apply tags the commit that landed.
- If a queue stalls, open a pull request turning that repository's switch off; the owner merges it with
  `gh pr merge --rebase --admin`, or disables the rule on GitHub. Report it on #197 and reopen it.
- Comment on #197 with the PR, the archived change and each repository's first queued pull request; check it's closed
  and its card says Done.
