# Tasks

## 1. Prove the reservation (design D1). If it fails, stop here

- [ ] 1.1 Create private `troupe-run/infra-probe-dependabot-branches` (ask the owner to run `gh repo create` if the
  permission check refuses it) with a `package.json` and `package-lock.json` pinning a package one patch release
  behind, a `.github/dependabot.yml` for `npm` (weekly, no cooldown), and delete-on-merge on. Add D2's ruleset with
  `gh api -X POST repos/troupe-run/infra-probe-dependabot-branches/rulesets`: `refs/heads/dependabot/**`, `creation`
  and `update`, `update_allows_fetch_and_merge` false, one bypass actor `Integration` 29110 `always`. Verify GitHub
  accepts it (`gh api .../rulesets/<id>` shows the bypass actor), and record the response here
- [ ] 1.2 Verify Dependabot opens its pull request under the ruleset (trigger a run from the repository's Dependabot
  page, or wait for the first run after the config lands), then push a commit to `main` and comment
  `@dependabot rebase`, and verify the branch is force-pushed. Record both, with the branch's SHAs
- [ ] 1.3 Hand the owner the commands to try, with their login: push a new branch `dependabot/npm_and_yarn/x`, push a
  commit to Dependabot's branch, and press "Update branch" on its pull request. Verify each is refused by the ruleset
  and the branch is unchanged. Then merge Dependabot's pull request and verify its branch is deleted. Record each
  result here
- [ ] 1.4 Delete the probe repository (`gh repo delete --yes`) and verify `gh repo view` says it doesn't exist. If
  1.1, 1.2's opening, or 1.3's refusals failed: record it here, comment on #174 with what failed, tell the owner, and
  stop (owner, 2026-10-26). If only the rebase or the deletion failed: ask the owner before going on

## 2. Pin what must not change

- [ ] 2.1 Before touching `scripts/guard.py`, add tests in a new `scripts/tests/test_guard_dependabot.py` that pass on
  `1d425ec`'s guard: `run_ci` refuses under `commit-branch-change` a qualifying `dependabot/npm_and_yarn/zod-4.6.7`
  branch (real commit message from website #44, `package-lock.json` only) with `repository` `troupe-run/.github`,
  with `None`, and in a fork; a release branch in troupe still passes; and the local pre-commit
  `commit_branch_change` refuses a commit on a `dependabot/` branch. Verify they pass with `scripts/guard.py` unchanged,
  and record the run

## 3. The ruleset (design D2)

- [ ] 3.1 In `tofu/dependabot.tf`, add `local.dependabot_app_id = 29110` (with a comment citing `gh api
  /apps/dependabot` and 1.1) and `github_repository_ruleset.dependabot_branches`, `for_each` over
  `local.dependabot_files`' keys, copying `release_branches`' shape, with a header comment citing the spec and D2.
  Give `github_repository_file.guard` a `depends_on` on it. Verify `tofu fmt -check` and `tofu validate` pass
- [ ] 3.2 Generalise `release_ruleset_repositories` in `scripts/tests/test_guard_push_and_ci.py` to take the ref
  pattern and file (or add `dependabot_ruleset_repositories` beside it, reading `for_each` over
  `local.dependabot_files`). Add tests: every repository in `guard.DEPENDABOT_REPOSITORIES` is covered; removing the
  ruleset, setting `creation` or `update` false, or changing the pattern leaves them uncovered; the only bypass actor
  is 29110. Add a test in the Dependabot config tests that no generated entry sets `pull-request-branch-name`. Verify
  each removal test fails the coverage assertion, and `uv run pytest -m tofu` passes
- [ ] 3.3 Run a local plan (fast-forward onto `origin/main` first) and verify it adds exactly three
  `dependabot_branches` rulesets, for troupe, website and infrastructure, and changes the delivered `scripts/guard.py`
  in troupe and website, and nothing else. Record the plan's summary here

## 4. The exemption (design D3-D6)

- [ ] 4.1 Add `DEPENDABOT_BRANCH_PREFIX`, `DEPENDABOT_REPOSITORIES` (troupe, website, infrastructure, with a docstring
  naming `tofu/dependabot.tf`), `DEPENDENCY_FILES`, and copies of `TITLE`, `VERSION` and `update_type` from
  `scripts/dependabot_issues.py`, each citing design D4/D5. Add a differential test in `test_guard_dependabot.py`
  that the guard's kind equals `dependabot_issues.read_update`'s for the seven real subjects in the design's table
  and for hypothesis-generated version pairs. Verify it passes, and fails when the guard's copy counts the third part
  as minor
- [ ] 4.2 Add the files condition (D4): every path modified (`M`), named in `DEPENDENCY_FILES` or a workflow whose
  every changed line is a `uses:` line. Verify with tests: `package-lock.json` alone, `package.json` with it,
  `pyproject.toml` in two packages with `uv.lock`, and infrastructure #184's `tofu.yml` diff each qualify;
  `src/index.ts`, a deleted `uv.lock`, a renamed `package.json`, and a workflow with a changed `run:` line each fail
  and are named. Add a test that every ecosystem in `tofu/labels/dependabot.json` has its files in `DEPENDENCY_FILES`
  (or is `github-actions`)
- [ ] 4.3 Add the kind condition (D5): every commit's subject read with `TITLE`, counted minor or patch, and every
  `update-type:` line semver-minor or semver-patch. Verify with tests on the real messages: #44, #54 (no
  `update-type`), #58 and #174 qualify; #55 fails as major; #175 fails as unreadable; a `1.2.3 → 1.2.4` subject with
  `semver-major` fails; a branch with two commits, one major, fails
- [ ] 4.4 Wire `exempt_dependabot_branch` into `run_ci` (D6): skip `commit_branch_change` when it holds; for a
  `dependabot/` branch in a reserved repository that fails, add the failed condition to the refusal's problem and the
  OpenSpec-change fix with the docs link. Replace D5's pinning test with the spec's scenarios: the qualifying patch,
  minor, push and author-isn't-Dependabot cases pass in each of the three repositories; 2.1's cases still refuse;
  a qualifying branch with no closing line fails only `pr-closes-issue`; a non-conventional Dependabot commit still
  fails `commit-message`. Verify that replacing the exemption with `False` fails the qualifying tests and that the
  refusal tests assert the reason text. Run `uv run pytest` and `uv run scripts/check.py`
- [ ] 4.5 Update `docs/development-workflow.md`: the `commit-branch-change` row describes the Dependabot exemption
  (reserved name, `DEPENDABOT_REPOSITORIES`, dependency files, minor or patch, authors not read); the `pr-closes-issue`
  row still says Dependabot isn't exempt from it; the "Dependabot pull requests" section is rewritten for both paths:
  minor and patch merge as they are, majors and anything else take an OpenSpec change as D5 described, use
  `@dependabot rebase` rather than "Update branch", and the D5 test sentence goes. Update `.github/workflows/guard.yml`'s
  header comment only if it lists exemptions. Verify `uv run pytest scripts/tests/test_guard_docs.py` and
  `uv run scripts/check.py` pass

## 5. Integration checks

- [ ] 5.1 Probe the branch's guard on scratch clones, with `GITHUB_EVENT_NAME=pull_request`, hand-written payloads
  naming the head repository, and nothing pushed: website at #44's head (passes, given a closing body) and #55's
  head (fails `commit-branch-change`, saying major); troupe at #174's head (passes) and #175's (fails, versions
  unreadable); infrastructure at #184's head (passes). Record each output here, and delete the clones
- [ ] 5.2 Push the branch and open the pull request with `Closes #174`. Verify its `guard` run passes and its plan
  comment matches 3.3. Record the PR, the run and the plan

## Workflow follow-up

- Archive the change on the branch before asking for the plan's approval, and rebase onto `main`'s state commit, so
  the approval is asked once.
- After the owner merges and approves the apply: verify the three rulesets exist (`gh api repos/troupe-run/<repo>/rulesets`)
  and the next plan is clean. Then comment `@dependabot rebase` on website #44, #45 and #46 (or their successors) and
  on infrastructure's open Dependabot pull requests, and verify each patch or minor one's `guard` passes and website
  #55 still fails naming the major update. Record the runs on #174.
- Comment on #174 with the PR and the archived change, check it's closed and its card says Done. #170 stays open
  until its other sections are done.
