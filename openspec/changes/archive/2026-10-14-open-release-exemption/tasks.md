# Tasks

## 1. The exemption holds only where the branch's repository has the release ruleset

- [x] 1.1 Write failing tests in `scripts/tests/test_guard_push_and_ci.py`, each named for what its body checks
      (design D1, D5). Give `run_ci` the repository the branch lives in. The section keeps its monkeypatched test
      address until 3.1 fills the real one, which then replaces it. Then: the bot's `release-please--branches--main`
      in `troupe-run/troupe` passes; the same branch in `troupe-run/infrastructure` fails on `commit-branch-change`;
      in a fork's name (`someone/troupe`) it fails on `commit-branch-change`; with no repository it fails on
      `commit-branch-change`. Keep the existing cases (someone else's commit alone or after the bot's, another branch
      name, a non-conventional bot commit, a branch adding nothing, the force-push range), each in
      `troupe-run/troupe`. Verify the new ones fail with `uv run pytest scripts/tests/test_guard_push_and_ci.py`
- [x] 1.2 Add `RELEASE_REPOSITORIES = frozenset({"troupe-run/troupe"})` beside `RELEASE_AUTHOR_EMAIL`, with a
      docstring naming `tofu/release.tf`. Make `release_branch_by_the_bot` and `run_ci` take the repository, and exempt
      nothing unless it's in the set (design D1). Verify 1.1's tests pass, all of `scripts/tests/` passes, and
      `uv run scripts/check.py` passes (mypy --strict, ruff)
- [x] 1.3 Write a test that reads `tofu/release.tf` and checks that a `github_repository_ruleset` including
      `refs/heads/release-please--*` is declared for each repository in `guard.RELEASE_REPOSITORIES`. Map
      `module.repo_troupe.name` to `troupe-run/troupe` the way `tofu/repositories.tf` names it (design D4). Verify it
      passes, and that it fails when the ruleset block is removed from a temporary copy of the file

## 2. The repository comes from GitHub

- [x] 2.1 Write failing tests (design D2): `github_ci_inputs` returns `GITHUB_REPOSITORY` for a push and `None` when
      it's unset; for a `pull_request` payload it returns `pull_request.head.repo.full_name` (the fork's name for a
      fork) and `None` when `head.repo` is `null`; for a `head.repo` that's present but not an object with a string
      `full_name`, `guard.py ci` exits 1 with a refusal saying it couldn't read the head repository, to re-run, and
      to tell the owner if it fails again; `guard.py ci --head <sha> --branch release-please--branches--main
      --repository troupe-run/troupe` on the bot's branch exits 0, and with `--repository troupe-run/infrastructure`
      exits 1 naming `commit-branch-change`. Verify they fail
- [x] 2.2 Add the repository to `github_ci_inputs`, `UnreadableHeadRepositoryError` reported by `run_ci_entry`, and
      `--repository` to `guard.py ci` (design D2). Verify 2.1's tests pass, all of `scripts/tests/` passes, and
      `uv run scripts/check.py` passes

## 3. The address is filled

- [x] 3.1 Re-check the bot's ID with `gh api 'users/troupe-run-release%5Bbot%5D' --jq '{id,login,type}'` (expect
      341990208, `troupe-run-release[bot]`, `Bot`). Then set
      `RELEASE_AUTHOR_EMAIL = "341990208+troupe-run-release[bot]@users.noreply.github.com"`, keeping its
      `str | None` type, and rewrite its docstring (design D3): filled after the `release branches` ruleset was applied
      (#41); the ruleset is the hard check and the author check alone isn't; it applies only in
      `RELEASE_REPOSITORIES`; `None` closes the exemption again. Switch the release-please tests from the
      monkeypatched test address to `guard.RELEASE_AUTHOR_EMAIL`, authored as `troupe-run-release[bot]`, except the
      `None` test, which keeps its monkeypatch (design D5). Verify all of `scripts/tests/` passes and
      `uv run scripts/check.py` passes

## 4. Docs

- [x] 4.1 Update `docs/development-workflow.md`. The `commit-branch-change` row: the exemption is open, only in a
      repository named in `RELEASE_REPOSITORIES` (troupe), and for a pull request only from a branch in that same
      repository, not a fork; drop "empty until the App exists". The known gap "The release-branch exemption trusts
      the commit's author": the ruleset is applied on troupe, the exemption applies nowhere else, and a fork's branch
      isn't exempt. Update the README's "release branches" paragraph to match. Verify `test_guard_docs.py` passes and
      `uv run scripts/check.py` passes

## 5. Evidence

- [x] 5.1 Dry run in a throwaway local repository (no GitHub). Use a bare remote holding `main` and a
      `release-please--branches--main` branch whose only commit is authored by
      `troupe-run-release[bot] <341990208+troupe-run-release[bot]@users.noreply.github.com>`. Run this branch's
      `scripts/guard.py ci --head … --branch … --repository troupe-run/troupe` (exit 0), then the same with
      `troupe-run/infrastructure` and with `someone/troupe` (exit 1, `commit-branch-change`). Add a commit by another
      author and run with `troupe-run/troupe` (exit 1). Record the commands and output here
      Done 2026-10-14 with `env -u CLAUDE_PROJECT_DIR -u GITHUB_EVENT_NAME -u GITHUB_REPOSITORY uv run --no-project
      python scripts/guard.py ci --base <main> --head <sha> --branch release-please--branches--main --repository …`.
      Bot's only commit (1750562): `troupe-run/troupe` exit 0, "every rule passes for
      release-please--branches--main"; `troupe-run/infrastructure`, `someone/troupe` and no `--repository` each
      exit 1, "guard: commit-branch-change: branch 'release-please--branches--main' has no matching OpenSpec
      change". With `fix: slip something in` by another author added (bcb39db), `troupe-run/troupe` exit 1, the same
      `commit-branch-change` refusal
- [x] 5.2 Run `uv run scripts/tofu.py plan` (after fast-forwarding onto `origin/main`) and verify it shows only the
      delivered `scripts/guard.py` changing in troupe; keep it for the pull request
      Done 2026-10-14 on a branch level with `origin/main`: `Plan: 0 to add, 1 to change, 0 to destroy.`, the one
      change being `github_repository_file.guard["troupe:scripts/guard.py"]` updated in place
- [x] 5.3 Run `openspec validate open-release-exemption --strict` and verify it passes

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #42`, the dry run from 5.1 and the plan from 5.2. CI
  must be green on all three OSes before the delivery is planned.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers `scripts/guard.py` to troupe.
- After the apply, confirm troupe's `scripts/guard.py` matches `main` here, and that troupe's `guard` run on the
  delivery commit passes. Then comment on #42 with the pull request and the archived change, and on
  troupe-run/troupe#23 that the exemption is open.
- When troupe#23's first release PR opens, check that its `guard (workflow rules)` run passes and that its commit's
  author is `341990208+troupe-run-release[bot]@users.noreply.github.com`, and record it on #42. If the author
  differs, the PR fails closed on the branch rule; a follow-up names the observed identity (design, Risks).
