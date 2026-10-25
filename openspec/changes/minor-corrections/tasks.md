# Tasks

## 1. Wording (#103 comments 1 and 2; design D4)

- [x] 1.1 In `docs/development-workflow.md`'s "Known gaps" (line 327), replace the #101 sentence with "Giving agents
  a GitHub login of their own, which GitHub would then hold to its rules, was parked in #101: troupe will decide
  actors' credentials (troupe-run/troupe#11)." Verify `uv run pytest scripts/tests/test_guard_docs.py` passes
- [x] 1.2 In `README.md` (lines 84-85) and `.github/workflows/schedules.yml` (lines 17-18), use #103's suggested
  wording: GitHub doesn't define activity, and commits (merges, and the App's state commits) are assumed to count.
  Verify by reading both against the comment, and verify `uv run scripts/check.py` passes (workflow lint included)

## 2. Pin what must not change, before the index fix

- [x] 2.1 In `scripts/tests/test_guard_git_hooks.py`, add end-to-end hook tests in a temporary repository with the
  hooks on. First, a plain `git commit` with an unstaged tracked edit is refused under `commit-checks`, naming the
  file. Second, a plain commit of only staged `openspec/` paths skips the check. Third, `git commit <path>` with another
  edited tracked file left out is refused under `commit-checks`, naming that file (spec: "Committing named paths
  with other edits left out"). Verify all three **pass on the unchanged guard**, and commit them. Found doing it: on
  the unchanged guard, `git commit a.txt` with `a.txt` unstaged names `a.txt` too, the file being committed (the same
  bug as `-a`), so the pinned test asserts only that the left-out `b.txt` is named
- [x] 2.2 Add the failing side, end to end: `git commit -a` with an unstaged tracked edit is made. `git commit -a`
  of an unstaged edit to `scripts/check-paths.toml` runs the full check. `git commit -a` of an edit leaving an
  archived change's task unticked is refused, naming the task. In a repository with a delivery list, `git commit -a`
  of an edit to a delivered file is refused under `delivered-file`. Also: a malformed declaration committed with
  `-a` is refused for the declaration; a path commit names only the edits it leaves out; and a path commit leaving
  out a file staged in `.git/index` is refused naming it (owner, 2026-10-25: refuse, as D2 says). Verify each
  **fails** on the unchanged guard for the reason named, and commit them marked `xfail(strict=True, reason="#103")`

## 3. The pre-commit hook reads the committing index (design D1, D2)

- [x] 3.1 In `scripts/guard.py`, add `_committing_env(root)` and rebuild `committing_paths` on it. Verify the
  existing commit-msg tests in `test_guard_git_hooks.py` still pass unchanged
- [x] 3.2 Make `ReadStaged`, `commit_checks`' two diffs and `run_pre_commit`'s staged list use it, and add D2's
  path-commit wording to the `commit-checks` fix. `test_a_staged_schema_left_out_of_a_pathspec_commit_doesn_t_count`
  is then refused by `commit-checks` (the left-out schema is in the working tree), so rework it to call the
  commit-msg entry with a `next-index` lock as git builds it, as its siblings do. Verify by removing the `xfail` marks
  from 2.2: every test in group 2 and the reworked schema test pass, and the path-commit refusal names the new fix
- [x] 3.3 Add a test that `_committing_env` resolves a relative `GIT_INDEX_FILE` against the root, leaves an absolute
  one alone, and adds nothing when it's unset, and that `scripts/check.py` is still started without it. Verify they
  pass, and that the relative case fails if the resolution is removed (check by hand, then restore)
- [x] 3.4 In `docs/development-workflow.md`, make the `commit-checks`, `delivered-file` and archived-tasks rows say
  they judge what the commit contains, including with `git commit -a` or `git commit <path>`, and update the
  `commit-checks` fix text. Verify `uv run pytest scripts/tests/test_guard_docs.py` passes, and read the rows
  against `run_pre_commit`

## 4. A force-pushed branch is judged on GitHub (design D3)

- [x] 4.1 In `scripts/tests/test_guard_push_and_ci.py`, pin the unchanged cases: a push whose `before` is in the
  clone gives `before` as the base, and the existing release-branch force-push test still passes. Add the failing
  case: a branch with a non-conventional commit is rebased onto a newer `main`, its old tip is dropped from the clone
  (`git reflog expire` and `git gc --prune=now`, or a fresh clone), and a push event names that tip. `guard.py ci`
  must then fail under `commit-message`, naming the commit. Verify the pinned cases pass and the new one **fails** on
  the unchanged guard. Commit it `xfail(strict=True, reason="#103")`
- [x] 4.2 In `github_ci_inputs`, keep a push's `before` only when `git cat-file -e <before>^{commit}` succeeds, and
  otherwise use the merge-base with `origin/main` and print D3's note. Verify by removing the `xfail`: 4.1's test
  passes, its output contains the note, and every other test in the file passes
- [x] 4.3 In `docs/development-workflow.md`, say that a push whose previous tip isn't in the clone is judged from
  where the branch left `main`. Verify by reading it against `github_ci_inputs`. Found doing it: line 151 is about
  `ci.yml`'s check-scope job, whose full-check fallback on a force push is right, so the sentence went where the
  docs say the `guard` check runs on a push (line 30), and design D4 says so

## 5. Integration

- [ ] 5.1 In a scratch clone of troupe at `origin/main` with the new `scripts/guard.py` and its hooks on, verify:
  `git commit -a` of a tracked edit runs the check and commits; `git commit <path>` with another edit left out is
  refused naming it. Record both in the pull request
- [ ] 5.2 Run `uv run scripts/check.py` and `openspec validate minor-corrections --strict`, and verify both pass
- [ ] 5.3 After rebasing onto `origin/main`, run `uv run scripts/tofu.py plan`, and verify it shows only
  `scripts/guard.py` updated in place in troupe and website. Keep it for the pull request

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #103`, with the evidence from 5.1 and the plan from 5.3.
  CI must be green on all three OSes before the delivery is planned. After the force-push fix is on the branch, check
  that the branch's own `guard` run after a rebase reports the note and a non-empty range.
- Tick, archive (running `openspec validate development-workflow --type spec --strict` on the synced main spec too),
  and rebase onto main's state commit in one push. Then ask once for the `plan-pr` approval.
- The owner merges by rebase and approves the `apply` job, which delivers `scripts/guard.py` to troupe and website.
  Confirm both delivered files match `main` here.
- Comment on #103 with the pull request and the archived change, check it's closed and its roadmap card says Done.
  Open the next "Minor corrections to batch" issue with `--project "troupe roadmap"`, check it's on the board, and
  update the minor-corrections memory to point at it.
