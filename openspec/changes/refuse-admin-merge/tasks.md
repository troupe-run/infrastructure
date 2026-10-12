# Tasks

## 1. The rules and the table (design D1–D3, D5)

- [x] 1.1 Add `owner-only` and `gh-allow-list` to `OVERRIDABLE_RULES`. Write the table as one constant in
  `scripts/guard.py`, grouped as in D3. Write `gh_decision(words, cwd)`, which:
  - reads gh's subcommand, flags, method, endpoint and GraphQL query (D3, "How gh is read");
  - finds the target repository (D2);
  - returns `owner-only` before `gh-allow-list` (D1), with D5's messages.

  Call it for each simple command in `shell_decisions`. Standard library only. Verify:
  - `mypy --strict` and `ruff` are clean;
  - `scripts/check.py` passes.
- [ ] 1.2 Write `scripts/tests/test_guard_gh.py`, each test named for what its body checks.
  - **Reads are allowed:** one test per read row of D3, plus `GET` with `-X GET` and fields, and a GraphQL query with
    no mutation.
  - **Workflow writes are allowed:** one test per row, including `pr merge` without `--admin`, and each listed REST
    endpoint and GraphQL mutation.
  - **`owner-only` refuses each group of D3**, each with its message group:
    - merge, deployment, gates, administration and credentials;
    - endpoint forms: a full `https://api.github.com/` URL, a leading `/`, `{owner}/{repo}` placeholders, and the
      implicit `POST` from `-f`;
    - `--admin=true`;
    - GraphQL from inline, from `query=@file`, and from `--input <file>`;
    - a repository outside `troupe-run`.
  - **`gh-allow-list` refuses:**
    - an unknown subcommand, `extension`, `alias set`, and a subcommand an alias would define;
    - an unlisted `gh api` write;
    - a GraphQL query from `@-`, from `--input -`, and from a missing file, each with its fix;
    - a query mixing a listed mutation with an unlisted one.
  - **Throwaway repositories (D2):**
    - creating and writing to `infra-probe-*`, `spike-*` and `bakeoff-*` is allowed, by `-R`, by an api path, and by
      `repo create`;
    - deleting `infra-probe-*` is allowed;
    - deleting, archiving and unarchiving `spike-*`/`bakeoff-*` is refused as `owner-only`;
    - the same prefixes outside `troupe-run` aren't throwaways.
  - **Mentions aren't commands:** a heredoc commit message or a quoted word naming `gh pr merge --admin` or
    `gh auth token` is allowed.
  - **Chaining:** `gh pr view 1 && gh pr merge 1 --admin` is refused.
  - **The survey:** a fixture of the distinct `gh` command shapes from D4 (one example per surveyed row, written into
    the test, with no transcripts read at test time). Each one is classified as D4's table says.
  - **End to end:** through `run_claude_pre_tool_use` with real-shaped JSON. An `owner-only` override lets exactly one
    refused command through, and a `gh-allow-list` override doesn't unlock an `owner-only` refusal.

  Verify: the tests pass locally, and on all three OSes in CI.
- [x] 1.3 Update `docs/development-workflow.md`:
  - a row for each rule in the rules table, saying what it refuses and its fix, and pointing to the table in
    `scripts/guard.py` rather than copying it;
  - D6's gaps under Known gaps.

  Verify:
  - `test_guard_docs.py` passes, so the doc lists exactly the guard's rules;
  - `scripts/check.py` passes.

## 2. Land it

- [ ] 2.1 Open the pull request (`Closes #16`). Its evidence:
  - the CI plan comment, after the owner approves the run. It must show only `scripts/guard.py` delivered to troupe;
  - the test output, including the survey test.

  Verify: every required check is green, and the plan comment matches.

## Workflow follow-up

- Archive on the branch before the merge (`/opsx:archive`), syncing the `development-workflow` spec.
- After the owner merges and approves the apply:
  - check the App's delivery commit to troupe, and troupe's `guard` and CI on it;
  - check that a manual `gh workflow run tofu.yml` reports no changes. Report the run links.
- In the next session, check that the everyday commands still go through (`gh pr view`, `gh run list`,
  `gh issue comment`), and note anything refused that should be on the list.
- Comment on #16 and close it.
