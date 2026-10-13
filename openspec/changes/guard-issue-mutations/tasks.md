# Tasks

## 1. No GraphQL mutation is allowed

- [x] 1.1 Change the tests in `scripts/tests/test_guard_gh.py` (design D1): replace
      `test_each_listed_graphql_mutation_is_allowed` with a test that each of the six formerly listed mutations and
      #30's three is refused as `gh-allow-list`; change the survey case for `updateIssue` to expect `gh-allow-list`;
      move the mixed-query and unparseable-query tests off `updateIssue` as the "listed" example where it matters;
      add a test that `gh issue edit 29 --type Feature`, `--remove-type`, `--add-blocked-by 63`,
      `--remove-blocked-by 63` and `--add-sub-issue 64` are allowed. Verify the refusal cases fail with
      `uv run pytest scripts/tests/test_guard_gh.py`
- [x] 1.2 Empty `GH_MUTATIONS_ALLOWED` in `scripts/guard.py`, keeping the table (design D1). Verify 1.1's tests pass,
      a GraphQL query with no mutation is still allowed, and owner-only mutations are still `owner-only`

## 2. Name the mutation and its gh command when refusing

- [x] 2.1 Write failing tests in `scripts/tests/test_guard_gh.py`, each named for what it checks:
      each mutation in design D1's table is named in its refusal, and its fix names the `gh` command in that
      table; `addLabelsToLabelable`'s fix names `gh issue edit <n> --add-label <name>`; a mutation with no allowed
      equivalent (`deleteIssue`, `addPullRequestReview`) is named, and its fix names no `gh` command; a query with two mutations, one repeated,
      names each once, in query order; the GraphQL fix leaves out the `-X GET` note; a REST refusal's message is
      unchanged. Verify they fail
- [x] 2.2 Write the table's two consistency tests (design D2): every command in `GH_MUTATION_EQUIVALENTS`, with its
      placeholders filled, is allowed by the guard; no mutation in it is owner-only or in `GH_MUTATIONS_ALLOWED`.
      Verify they fail because the table doesn't exist yet
- [x] 2.3 Add `GH_MUTATION_EQUIVALENTS` next to `GH_MUTATIONS_ALLOWED`, and make the GraphQL refusal name the unlisted
      mutations and their equivalents (design D2, D3). Verify 2.1's and 2.2's tests pass, all of `test_guard_gh.py`
      passes, and `uv run scripts/check.py` passes (mypy --strict, ruff)

## 3. Docs

- [x] 3.1 Update the `gh-allow-list` row in `docs/development-workflow.md` (design D4). Verify `test_guard_docs.py`
      passes and `uv run scripts/check.py` passes

## 4. Evidence

- [ ] 4.1 In this session, with the new guard as the hook, run a refused `gh api graphql` mutation that changes
      nothing on GitHub (`updateIssueIssueType` with a dummy id is refused before it is sent), and quote the refusal.
      Verify it names the mutation and `gh issue edit <n> --type <name>`
- [ ] 4.2 Run `uv run scripts/tofu.py plan` and verify it shows only the delivered `scripts/guard.py` changing in the
      governed repositories; keep it for the pull request
- [ ] 4.3 Run `openspec validate guard-issue-mutations --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #30`, the refusal from 4.1 and the plan from 4.2.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers the guard to troupe.
- After the apply, confirm troupe's `scripts/guard.py` matches `main` here, then comment on #30 with the pull request,
  the archived change and the owner's answer on permission rules.
