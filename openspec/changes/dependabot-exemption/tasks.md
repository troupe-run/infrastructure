# Tasks

## 1. Prove the reservation (design D1). If it fails, stop here

- [x] 1.1 Create private `troupe-run/infra-probe-dependabot-branches` (ask the owner to run `gh repo create` if the
  permission check refuses it) with a `package.json` and `package-lock.json` pinning a package one patch release
  behind, a `.github/dependabot.yml` for `npm` (weekly, no cooldown), and delete-on-merge on. Add D2's ruleset with
  `gh api -X POST repos/troupe-run/infra-probe-dependabot-branches/rulesets`: `refs/heads/dependabot/**`, `creation`
  and `update`, `update_allows_fetch_and_merge` false, one bypass actor `Integration` 29110 `always`. Verify GitHub
  accepts it (`gh api .../rulesets/<id>` shows the bypass actor), and record the response here. Result: the probe
  is **public**, not private, because GitHub Free applies rulesets only to public repositories; the owner created it
  (the permission check refused the agent). `package.json` pins `ms` 2.1.2 (latest 2.1.3), with its lockfile, at
  331e582. The ruleset was POSTed *before* `dependabot.yml` landed, and GitHub accepted it with no 422: id 25932824,
  `rules` `creation` and `update`, `bypass_actors` `[{"actor_id":29110,"actor_type":"Integration","bypass_mode":
  "always"}]`, `current_user_can_bypass` `never` for the owner's login. `dependabot.yml` (npm, daily) landed at
  91717b0 at 14:06:56 AEST. **But that pattern matched nothing**: see 1.3. The probe went on with
  `refs/heads/dependabot/**/*` (ruleset 25933017, same rules and bypass actor), and design D2 now says so
- [x] 1.2 Verify Dependabot opens its pull request under the ruleset (trigger a run from the repository's Dependabot
  page, or wait for the first run after the config lands), then push a commit to `main` and comment
  `@dependabot rebase`, and verify the branch is force-pushed. Record both, with the branch's SHAs. Result: under
  the first ruleset Dependabot opened #1 (`dependabot/npm_and_yarn/ms-2.1.3`, a7d4a24, verified, by
  `dependabot[bot]`) at 14:07:57 and rebased it onto 8c73f85 as 149f73d, but that ruleset turned out to match no
  branch, so neither counts. Under `refs/heads/dependabot/**/*`, whose `creation` and `update` rules GitHub's
  `rules/branches/<name>` endpoint listed for the branch: `@dependabot rebase` after `main` moved to 4320b80
  force-pushed e1bfbec (parent 4320b80) at 14:12:11; and after #1 merged, pinning `debug` 4.4.1 and changing
  `dependabot.yml`, Dependabot **created** `dependabot/npm_and_yarn/debug-4.4.3` (61f944f, `dependabot[bot]`) and
  opened #2 at 14:13:55, with the rules endpoint listing ruleset 25933017's `creation` and `update` for it
- [x] 1.3 Hand the owner the commands to try, with their login: push a new branch `dependabot/npm_and_yarn/x`, push a
  commit to Dependabot's branch, and press "Update branch" on its pull request. Verify each is refused by the ruleset
  and the branch is unchanged. Then merge Dependabot's pull request and verify its branch is deleted. Record each
  result here. Result: run by the agent with the owner's `gh` login (`martin-at-hpsgd`, an org owner), which is the
  same identity. Under `refs/heads/dependabot/**`, pushing a new `dependabot/npm_and_yarn/x` **was allowed**, and
  `rules/branches/` listed no rule for it or for Dependabot's branch, while troupe's release branch lists its
  ruleset's. Three more rulesets were POSTed to find a pattern: `refs/heads/dependabot/**/*` and
  `refs/heads/dependabot/npm_and_yarn/*` matched both branches, `refs/heads/dependabot/*` didn't. Keeping only
  `**/*`, each was refused with `GH013: Repository rule violations`: creating `dependabot/npm_and_yarn/y` ("Cannot
  create ref due to creations being restricted"), a commit to the stray `x` branch, a commit to Dependabot's branch,
  and a force-push of `main` onto it; the branch stayed 149f73d. `gh pr update-branch 1` after `main` moved failed
  (GitHub's GraphQL returned only "Something went wrong", not the rule) and left the branch at 149f73d. Merging #1
  with delete-on-merge deleted `dependabot/npm_and_yarn/ms-2.1.3`
- [x] 1.4 Delete the probe repository (`gh repo delete --yes`) and verify `gh repo view` says it doesn't exist. If
  1.1, 1.2's opening, or 1.3's refusals failed: record it here, comment on #174 with what failed, tell the owner, and
  stop (owner, 2026-10-26). If only the rebase or the deletion failed: ask the owner before going on. Result: deleted;
  `gh repo view` says it can't resolve the repository. Nothing failed under `refs/heads/dependabot/**/*`, so the change
  goes on, with that pattern

## 2. Pin what must not change

- [x] 2.1 Before touching `scripts/guard.py`, add tests in a new `scripts/tests/test_guard_dependabot.py` that pass on
  `1d425ec`'s guard: `run_ci` refuses under `commit-branch-change` a qualifying `dependabot/npm_and_yarn/zod-4.6.7`
  branch (real commit message from website #44, `package-lock.json` only) with `repository` `troupe-run/.github`,
  with `None`, and in a fork; a release branch in troupe still passes; and the local pre-commit
  `commit_branch_change` refuses a commit on a `dependabot/` branch. Verify they pass with `scripts/guard.py` unchanged,
  and record the run. Result: 5 tests in `scripts/tests/test_guard_dependabot.py` (the three refusals,
  the local refusal, and troupe's release branch over the same base); with `scripts/guard.py` identical to
  `1d425ec`'s: 5 passed

## 3. The ruleset (design D2)

- [x] 3.1 In `tofu/dependabot.tf`, add `local.dependabot_app_id = 29110` (with a comment citing `gh api
  /apps/dependabot` and 1.1) and `github_repository_ruleset.dependabot_branches`, `for_each` over
  `local.dependabot_files`' keys, copying `release_branches`' shape, with a header comment citing the spec and D2.
  Give `github_repository_file.guard` a `depends_on` on it. Verify `tofu fmt -check` and `tofu validate` pass. Result: the ruleset
  uses `refs/heads/dependabot/**/*`, the pattern task 1 proved, and depends on the three repository modules as the
  delivered `dependabot.yml` does. `tofu fmt -check` and `tofu validate` pass
- [x] 3.2 Generalise `release_ruleset_repositories` in `scripts/tests/test_guard_push_and_ci.py` to take the ref
  pattern and file (or add `dependabot_ruleset_repositories` beside it, reading `for_each` over
  `local.dependabot_files`). Add tests: every repository in `guard.DEPENDABOT_REPOSITORIES` is covered; removing the
  ruleset, setting `creation` or `update` false, or changing the pattern leaves them uncovered; the only bypass actor
  is 29110. Add a test in the Dependabot config tests that no generated entry sets `pull-request-branch-name`. Verify
  each removal test fails the coverage assertion, and `uv run pytest -m tofu` passes. Result:
  `dependabot_ruleset_repositories` sits beside the other Dependabot tests in `test_guard_dependabot.py` rather than
  generalising the release reader, because this ruleset is one `for_each` block, not one block per repository. It also
  rejects a second bypass actor and the `**` pattern task 1.3 showed matches nothing. `DEPENDABOT_BRANCH_PREFIX` and
  `DEPENDABOT_REPOSITORIES` went into `scripts/guard.py` here, ahead of 4.1, since the test reads them. Each of the
  five weakenings (creation, update, pattern, another App, a second bypass actor) and removing the block leave the
  repositories uncovered. `test_no_real_configuration_moves_dependabots_branches_out_of_the_reserved_name` is in
  `test_dependabot_config.py`. `uv run pytest -m tofu`: 142 passed
- [x] 3.3 Run a local plan (fast-forward onto `origin/main` first) and verify it adds exactly three
  `dependabot_branches` rulesets, for troupe, website and infrastructure, and changes the delivered `scripts/guard.py`
  in troupe and website, and nothing else. Record the plan's summary here. Result: on be05322 (0 behind `origin/main`),
  after two failed tries (a 1Password authorisation timeout, then DNS failures reaching `api.github.com`): `Plan: 3 to
  add, 2 to change, 0 to destroy`. The three adds are `dependabot_branches` for infrastructure, troupe and website,
  each `refs/heads/dependabot/**/*`, `creation` and `update` true, `update_allows_fetch_and_merge` false, and one
  bypass actor, `Integration` 29110 `always`. The two changes are `github_repository_file.guard` for
  `scripts/guard.py` in troupe and website, `60135e3cf269` → `fc621d1fb36d`

## 4. The exemption (design D3-D6)

- [x] 4.1 Add `DEPENDABOT_BRANCH_PREFIX`, `DEPENDABOT_REPOSITORIES` (troupe, website, infrastructure, with a docstring
  naming `tofu/dependabot.tf`), `DEPENDENCY_FILES`, and copies of `TITLE`, `VERSION` and `update_type` from
  `scripts/dependabot_issues.py`, each citing design D4/D5. Add a differential test in `test_guard_dependabot.py`
  that the guard's kind equals `dependabot_issues.read_update`'s for the seven real subjects in the design's table
  and for hypothesis-generated version pairs. Verify it passes, and fails when the guard's copy counts the third part
  as minor. Result: the guard's `DEPENDABOT_SUBJECT`, `DEPENDABOT_VERSION` and
  `dependabot_update_kind` (named for the guard, not copied names), plus a test that the two patterns are textually
  equal. The differential tests run over 8 real subjects (#175's commit subject and its PR title both) and hypothesis
  pairs, of versions and of whole `Bump … from … to …` subjects. With the third part counted as minor: 6 failed;
  restored, all pass
- [x] 4.2 Add the files condition (D4): every path modified (`M`), named in `DEPENDENCY_FILES` or a workflow whose
  every changed line is a `uses:` line. Verify with tests: `package-lock.json` alone, `package.json` with it,
  `pyproject.toml` in two packages with `uv.lock`, and infrastructure #184's `tofu.yml` diff each qualify;
  `src/index.ts`, a deleted `uv.lock`, a renamed `package.json`, and a workflow with a changed `run:` line each fail
  and are named. Add a test that every ecosystem in `tofu/labels/dependabot.json` has its files in `DEPENDENCY_FILES`
  (or is `github-actions`). Result: `non_dependency_paths` reads `git diff-tree -r -M --name-status`, so a
  rename shows as one path. The four qualifying cases pass; `src/index.ts`, `uv.lock` deleted, `web/package.json`
  renamed, the workflow with a changed `run:` line, and pip's `requirements.txt` (D5's old case) each fail naming the
  path. The ecosystem test is tagged `labels`
- [x] 4.3 Add the kind condition (D5): every commit's subject read with `TITLE`, counted minor or patch, and every
  `update-type:` line semver-minor or semver-patch. Verify with tests on the real messages: #44, #54 (no
  `update-type`), #58 and #174 qualify; #55 fails as major; #175 fails as unreadable; a `1.2.3 → 1.2.4` subject with
  `semver-major` fails; a branch with two commits, one major, fails. Result: all as specified, with the refusal text asserted
  (`… is a major update`, `doesn't give one dependency's versions`, `says update-type: …`). #55 is refused for both
  its versions and its stated `semver-major`
- [x] 4.4 Wire `exempt_dependabot_branch` into `run_ci` (D6): skip `commit_branch_change` when it holds; for a
  `dependabot/` branch in a reserved repository that fails, add the failed condition to the refusal's problem and the
  OpenSpec-change fix with the docs link. Replace D5's pinning test with the spec's scenarios: the qualifying patch,
  minor, push and author-isn't-Dependabot cases pass in each of the three repositories; 2.1's cases still refuse;
  a qualifying branch with no closing line fails only `pr-closes-issue`; a non-conventional Dependabot commit still
  fails `commit-message`. Verify that replacing the exemption with `False` fails the qualifying tests and that the
  refusal tests assert the reason text. Run `uv run pytest` and `uv run scripts/check.py`. Result: `dependabot_branch_change` wraps `commit_branch_change` in
  `run_ci`. D5's pinning test and its constants left `test_guard_push_and_ci.py`; its pip case is
  `test_a_file_dependabot_s_ecosystems_here_don_t_use_fails`. A branch not named `dependabot/` gets today's refusal
  word for word. With the exemption replaced by `False`: 13 failed (every qualifying case); restored:
  `test_guard_dependabot.py` 48 passed, and with `test_guard_push_and_ci.py`, `test_guard_pr_description.py` and
  `test_dependabot_config.py`, 159 passed. ruff and `mypy --strict` are clean. The full `scripts/check.py` runs in the
  commit hook
- [x] 4.5 Update `docs/development-workflow.md`: the `commit-branch-change` row describes the Dependabot exemption
  (reserved name, `DEPENDABOT_REPOSITORIES`, dependency files, minor or patch, authors not read); the `pr-closes-issue`
  row still says Dependabot isn't exempt from it; the "Dependabot pull requests" section is rewritten for both paths:
  minor and patch merge as they are, majors and anything else take an OpenSpec change as D5 described, use
  `@dependabot rebase` rather than "Update branch", and the D5 test sentence goes. Update `.github/workflows/guard.yml`'s
  header comment only if it lists exemptions. Verify `uv run pytest scripts/tests/test_guard_docs.py` and
  `uv run scripts/check.py` pass. Result: the `commit-branch-change` row adds the
  Dependabot exemption and its fix; the `pr-closes-issue` row already said a Dependabot pull request isn't exempt from
  it, and stays. The section now opens on the two paths, with the manual one kept for majors and the rest, and a
  paragraph on `@dependabot rebase` and on open pull requests picking the rule up only once rebased. The old D5 test
  sentence and website's DCO aside went. `guard.yml`'s header lists no branch exemption, so it's unchanged.
  `test_guard_docs.py`: 3 passed; `scripts/check.py` runs in the commit hook
- [x] 4.6 From the review on #193: trust only Dependabot's shape, `dependabot/<ecosystem>/<name>`, which the probe
  showed the ruleset reserves, not any name under `dependabot/`. Verify with a test that `dependabot/zod-4.6.7`,
  `dependabot/npm_and_yarn/` and `dependabot/` are refused with today's refusal in website, and that it fails under
  the old prefix test. Result: `DEPENDABOT_BRANCH` (`dependabot/[^/]+/.+`, fullmatch) in `reserved_dependabot_branch`;
  `test_a_name_not_shaped_like_dependabot_s_isn_t_trusted`. With `startswith(DEPENDABOT_BRANCH_PREFIX)` restored: 3
  failed; with the fix: `test_guard_dependabot.py` 51 passed. The spec gained the scenario, design D3 and the
  `commit-branch-change` row say so

## 5. Integration checks

- [x] 5.1 Probe the branch's guard on scratch clones, with `GITHUB_EVENT_NAME=pull_request`, hand-written payloads
  naming the head repository, and nothing pushed: website at #44's head (passes, given a closing body) and #55's
  head (fails `commit-branch-change`, saying major); troupe at #174's head (passes) and #175's (fails, versions
  unreadable); infrastructure at #184's head (passes). Record each output here, and delete the clones. Result: fresh
  clones in the scratchpad, this branch's guard at be05322, `GITHUB_EVENT_NAME=pull_request` with each pull request's
  real title, description and head repository from `gh pr view`. website #44 (a90da16), troupe #174 (2ac4eb7) and
  infrastructure #184 (9401d74): `every rule passes`, exit 0. website #55 (334f684): exit 1, `commit-branch-change`
  only, `… is a major update; 334f684's message says update-type: version-update:semver-major`. troupe #175 (e0e168b):
  exit 1, `commit-branch-change` only, `… subject 'chore(deps-dev): Update uv-build requirement' doesn't give one
  dependency's versions`. The other 13 open Dependabot pull requests (website #45, #46, #54, #56-#59; troupe #172,
  #173; infrastructure #182, #183, #185, #186) each pass, so `pr-closes-issue` is satisfied by the issue workflow's
  lines too. A first run judged `main`'s tip by mistake (the probe script set each `pr-<n>` to `FETCH_HEAD`, which was
  `main`); with an empty range the guard refused saying the branch `carries no commits`. The clones were deleted;
  nothing was pushed
- [ ] 5.2 Push the branch and open the pull request with `Closes #174`. Verify its `guard` run passes and its plan
  comment matches 3.3. Record the PR, the run and the plan

## Workflow follow-up

- Archive the change on the branch before asking for the plan's approval, and rebase onto `main`'s state commit, so
  the approval is asked once.
- After the owner merges and approves the apply: verify the three rulesets exist (`gh api repos/troupe-run/<repo>/rulesets`)
  and the next plan is clean. **Must pass before anything relies on the exemption:** for a name one level deeper than
  the probe tried, in each repository, `gh api repos/troupe-run/<repo>/rules/branches/<name>` lists the ruleset's
  `creation` and `update`: website `dependabot/npm_and_yarn/axe-core/playwright-4.14.0` (#58), infrastructure
  `dependabot/github_actions/actions/download-artifact-8.0.2` (#184), and troupe a two-level name and an invented
  three-level one. If any doesn't, the exemption covers branches GitHub doesn't reserve: tell the owner at once, don't
  rebase any Dependabot pull request, and fix the pattern in a change of its own before anything else. Then comment `@dependabot rebase` on website #44, #45 and #46 (or their successors) and
  on infrastructure's open Dependabot pull requests, and verify each patch or minor one's `guard` passes and website
  #55 still fails naming the major update. Record the runs on #174.
- Comment on #174 with the PR and the archived change, check it's closed and its card says Done. #170 stays open
  until its other sections are done.
