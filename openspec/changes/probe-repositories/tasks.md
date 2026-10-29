# Tasks

## 1. Pin what must not change (design D4)

- [x] 1.1 Before touching `scripts/guard.py`, add tests to `scripts/tests/test_guard_gh.py`: a repository name built
  by the shell (`troupe-run/$P`, `${P}`, `$(echo infra-probe-x)`, backticks, `infra-probe-$N`, through the
  `gh repo create` positional, `-R`, `GH_REPO=` and a `gh api` `repos/troupe-run/$P/git/refs` endpoint) is refused
  with the same rule as a live repository (`owner-only`, or `gh-allow-list` for the endpoint); #216's exact chained
  command is refused only for its `gh repo create`, and its `gh repo edit --help | grep ...` part goes ahead;
  `gh repo view troupe-run/$P` is allowed. Run them on the unchanged guard and verify they pass
- [x] 1.2 Add tests that a literal probe's writes #217 names are allowed (`gh api -X POST
  repos/troupe-run/infra-probe-x/git/refs`, `gh api -X PATCH repos/troupe-run/infra-probe-x -F
  has_pull_requests=false`, `gh api -X PUT .../contents/<file>`, `gh pr create -R troupe-run/infra-probe-x` with no
  closing reference), and that `gh api graphql` with an `updateRepository` mutation is refused as an unlisted
  mutation (spec scenario "A GraphQL mutation on a probe", design D2). Verify they pass on the unchanged guard

## 2. The refusal says why (design D1)

- [x] 2.1 Add tests for the spec scenario "A probe named through a variable": each shell-built case from 1.1 that's
  refused has a problem naming the word and saying the guard judges it as a live repository, and a fix that keeps
  the rule's own fix first and then says to write a throwaway repository's name out. Add the scenario "A live
  repository's refusal is unchanged": `gh repo create troupe-run/my-repo --public` has today's `owner-only`
  message exactly. Verify the new tests fail on the unchanged guard
- [x] 2.2 In `scripts/guard.py`, add `_named_by_shell(repository)` (true when the name holds `$` or a backtick,
  with a docstring citing GitHub's name rules and this design) and apply it to a refusal at the end of
  `gh_decision`, for both the `gh api` and subcommand paths, keeping the rule. Verify 2.1's tests and 1.1-1.2's pins
  pass, and that `uv run pytest scripts/tests/test_guard_grants.py` still passes (the guard grants nothing new)

## 3. Docs (design D3)

- [x] 3.1 In `docs/development-workflow.md`, add a "Throwaway repositories" section after "Which commands the guard
  reads": the names and which are kept, what an agent may do with the command for each (create, configure, push,
  pull requests and issues, delete), what isn't exempt (credentials, extensions and aliases, GraphQL mutations, a
  name built by the shell), that the name must come from `-R`, `GH_REPO` or the positional, and that installing the
  App on a probe is the owner's. Verify each command it names is allowed by running it through `shell_decisions` in a
  scratch script (not committed), and that each "isn't exempt" example is refused
- [x] 3.2 Cut the `owner-only` row's exemption sentence to a pointer to the new section, keeping its exceptions for
  `spike-*` and `bakeoff-*` records and its help sentence; add the same pointer to the `gh-allow-list` row; rewrite
  the "Known gaps" bullet "A throwaway repository is a naming convention" to point there too. Verify
  `uv run pytest scripts/tests/test_guard_docs.py` passes

## 4. Checks and plan

- [ ] 4.1 Run `uv run scripts/check.py` (ruff, mypy --strict, pytest, OpenSpec strict validation including this
  change) and verify it passes
- [ ] 4.2 Fast-forward onto `origin/main`, run a local plan, and verify it changes only the delivered
  `scripts/guard.py` in troupe and website

## Workflow follow-up

- Open the pull request with `Closes #216` and `Closes #217`; the owner approves the plan run; act on Claude's review
  of the last push.
- Archive on the branch before the merge; the owner merges by rebase.
- Open the successor "Minor corrections to batch" issue with `--project "troupe roadmap"`, saying it follows #216,
  and update the minor-corrections memory to name it. Update the throwaway-repo-naming memory: `gh api -X PATCH
  repos/<probe>` is allowed (it said refused), and the `$P` cause.
- Comment on #216 and #217 with the pull request and the archived change; check both are closed and their cards are
  Done.
