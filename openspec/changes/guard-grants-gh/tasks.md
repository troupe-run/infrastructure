# Tasks

## 1. What is granted

- [x] 1.1 Write failing tests in a new `scripts/tests/test_guard_grants.py`, each named for what it checks:
      `GH_GRANTED` is a subset of `GH_READS ∪ GH_WORKFLOW_WRITES`; it holds no `pr merge`, `pr checkout`,
      `workflow run`, `run rerun` or `run cancel` (design D1). Verify they fail because the table doesn't exist
- [x] 1.2 Add `GH_GRANTED` to `scripts/guard.py` next to the allow-list tables (design D1). Verify 1.1's tests pass

## 2. Only plain commands are granted

- [x] 2.1 Write failing tests for `grantable` (design D2), each named for what it checks. Granted:
      `gh pr ready 74`, `gh issue edit 29 --type Feature`, `gh issue comment 1 --body "Fix #3"`,
      `gh pr view 17 --json comments --jq '.comments[]'`, a `--body-file` inside the repository and one under the temp
      directory. Not granted, each on its own:
      - `gh pr merge 32 --rebase`, `gh workflow run tofu.yml`, `gh api repos/troupe-run/troupe`;
      - a write to `troupe-run/infra-probe-x`;
      - `gh pr ready 74 && rm -rf build`, `gh pr ready 74; ls`, `gh pr ready 74 | cat`;
      - `gh issue comment 1 --body "$(cat notes)"`, ``--body "`id`"``, `--body "$HOME"`;
      - `GH_TOKEN=x gh pr ready 74`, `/usr/local/bin/gh pr ready 74`, `gh pr ready 74 > out`;
      - a heredoc;
      - `--body-file ~/.ssh/id_ed25519`, `--body-file /etc/hosts`, `--body-file -`, and a symlink inside the
        repository pointing outside it;
      - a command any rule refuses.

      Verify they fail
- [x] 2.2 Implement `grantable(command, root)` in `scripts/guard.py` (design D2). Verify 2.1's tests pass and
      `uv run scripts/check.py` passes

## 3. Only the reviewed guard grants

- [x] 3.1 Write failing tests (design D3): with a test repository whose `origin/main` holds a byte-identical
      `scripts/guard.py`, the guard is reviewed. It isn't when the file differs, when `origin/main` doesn't exist, or
      when `origin/main` has no `scripts/guard.py`. Verify they fail
- [x] 3.2 Implement the check, taking the running guard's path as a parameter defaulting to `Path(__file__)` so tests
      can point it at a copy (design D3). Verify 3.1's tests pass

## 4. The hook

- [ ] 4.1 Write failing tests in `scripts/tests/test_guard_claude.py` (design D4): a granted Bash command prints
      `permissionDecision: "allow"` with a reason starting `guard:`; the same command through PowerShell prints
      nothing; with the guard differing from `origin/main` it prints nothing; a refused command still prints `deny`;
      a refusal excused by an override prints nothing. Verify they fail
- [ ] 4.2 Wire the grant into `run_claude_pre_tool_use` (design D4). Verify 4.1's tests and every existing hook test
      pass, and `uv run scripts/check.py` passes

## 5. Docs

- [ ] 5.1 Add "What the guard grants" and the two Known gaps entries to `docs/development-workflow.md` (design D5).
      Verify `test_guard_docs.py` and `uv run scripts/check.py` pass

## 6. Evidence

- [ ] 6.1 In the scratch repository, with this branch's `guard.py` committed as its `origin/main` and installed as the
      hook in headless `claude -p --permission-mode auto`, verify each of these and record the results for the pull
      request:
      - a granted read (`gh pr view 32 -R troupe-run/infrastructure --json state`) runs, with an `autoMode.hard_deny`
        canary in it that denies it without the hook;
      - a not-granted command with the same canary is still denied;
      - a granted command matched by an `ask` rule, and one matched by a `deny` rule, written in the scratch
        repository's `.claude/settings.local.json` (a real settings file, not `--settings`), still prompts or is
        refused. If a restricting rule there is ignored because the workspace isn't trusted, record that and ask the
        owner before changing any personal settings file.
- [ ] 6.2 Rebase onto `main` if #33 has merged, and rerun `uv run scripts/check.py`
- [ ] 6.3 Run `uv run scripts/tofu.py plan` and verify it shows only the delivered `scripts/guard.py` changing; keep it
      for the pull request
- [ ] 6.4 Run `openspec validate guard-grants-gh --strict`, and verify that the synced spec would also pass
      `openspec validate --specs --strict` (requirement text under 500 characters)

## Workflow follow-up

- Open the pull request with `Closes #31`, the evidence from 6.1 and the plan from 6.3.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers the guard to troupe.
- After the apply, confirm troupe's `scripts/guard.py` matches `main` here by blob hash, then comment on #31.
