# Tasks

## 1. Pin what must not change, before the rule exists

- [ ] 1.1 In `scripts/tests/test_guard_git_hooks.py`, add hook tests in a temporary repository with a
  `protocol/schemas/a.schema.json` committed: a `docs:` commit changing only `protocol/README.md` and
  `protocol/CHANGELOG.md` is made; a `chore:` commit in a repository with no `protocol/` is made; a `feat:` commit
  changing a schema is made. Verify all three **pass on the unchanged guard** (they pin the proposal's "unaffected"
  cases), and commit them
- [ ] 1.2 Add the failing side: a `docs(protocol):` commit changing `protocol/schemas/a.schema.json` is refused, with
  no commit made. Verify it **fails** on the unchanged guard (the commit is made), and commit it marked
  `xfail(strict=True, reason="#122")`
- [ ] 1.3 Add hook tests for how the commit was made (spec: "Only the files being committed count"): `git commit -a`
  with a schema edit under `docs:` is refused; `git commit protocol/README.md` under `docs:` with a schema edit left
  unstaged is made; staging a schema then committing only another path with `git commit <path>` under `docs:` is
  made. Verify the refusing case is `xfail(strict=True)` on the unchanged guard and the others pass
- [ ] 1.4 Record, in the pull request's notes, what the pre-commit hook's `git diff --cached` sees during
  `git commit -a` (`.git/index` versus `GIT_INDEX_FILE`), from a scratch repository with the hooks on. If its
  `commit-checks` or `delivered-file` reading is wrong there, comment on infrastructure#103 with the reproduction
  (design, Risks); don't change it here

## 2. The rule (design D1-D4, D6)

- [ ] 2.1 In `scripts/guard.py`, add `SCHEMA_PATHS` beside `RELEASE_REPOSITORIES` and `RELEASING_TYPES` beside
  `COMMIT_TYPES`, each with a docstring naming its source (troupe#140; release-please `src/util/filter-commits.ts`),
  and add `schema-commit-type` to `OVERRIDABLE_RULES`. Verify `uv run pytest scripts/tests/test_guard_docs.py` now
  fails, naming the undocumented rule
- [ ] 2.2 Add a pure decision `schema_commit_type(message, paths)`: allow when no path is under `SCHEMA_PATHS`, when
  the message isn't a Conventional Commit (left to `commit-message`), or when the type (after autosquash prefixes)
  is in `RELEASING_TYPES` or the commit is breaking (`!`, or a line starting `BREAKING CHANGE:` or
  `BREAKING-CHANGE:`); otherwise refuse naming up to five schema files, the type, the releasing types and the fix.
  Verify with parametrised tests in `scripts/tests/test_guard_commit_rules.py` covering every scenario of the spec's
  new requirement, including `fixup! docs: x` refused and `fixup! feat: x` allowed, a rename out of
  `protocol/schemas/`, and the refusal's text naming the files and every releasing type
- [ ] 2.3 Add a Hypothesis property test: for any accepted type, optional scope and `!`, and any set of paths, the
  decision refuses exactly when a path is under `protocol/schemas/` and the commit is neither of a releasing type nor
  breaking. Verify it passes, and that it fails when `RELEASING_TYPES` drops `perf` (check by hand, then restore)
- [ ] 2.4 Add a test pinning `RELEASING_TYPES` to the visible sections of release-please's
  `DEFAULT_CHANGELOG_SECTIONS` as read on 2026-10-23 (copied into the test with its source), and verify it passes
- [ ] 2.5 Call the rule from `run_commit_msg` after `commit_message`, with the staged paths read through the hook's
  `GIT_INDEX_FILE` when set (D4), every other git call still stripping it. Verify by removing the `xfail` marks from
  1.2 and 1.3: every test in groups 1 passes
- [ ] 2.6 Add the `schema-commit-type` row to `docs/development-workflow.md`'s rules table: what it refuses, where
  the paths and types are declared (`SCHEMA_PATHS`, `RELEASING_TYPES` in `scripts/guard.py`), that it's inert without
  `protocol/schemas/`, and the fix. Verify `uv run pytest scripts/tests/test_guard_docs.py` passes
- [ ] 2.7 Verify an owner's override excuses the rule once and is logged, as for the other git rules, with a test
  beside the existing override tests in `scripts/tests/test_guard_overrides.py`

## 3. Push and CI (design D5)

- [ ] 3.1 Add the range decision over commits (paths from `git diff-tree --no-commit-id --name-only --no-renames -r
  --root`), naming each failing commit as `<sha7> '<first line>' (<schema files>)`, and call it from `run_pre_push`
  and `run_ci`. Verify with tests in `scripts/tests/test_guard_push_and_ci.py`: a pushed commit reworded to
  `chore: tidy` after it changed a schema is refused, naming it; a pull request carrying a `--no-verify`
  `test:` schema commit fails the check under `schema-commit-type`; a range of releasing schema commits passes; a
  repository whose first commit adds a schema under `chore:` fails
- [ ] 3.2 Update the `pre-push` and GitHub check rows or prose in `docs/development-workflow.md` that list which rules
  each layer re-applies, so they name `schema-commit-type`. Verify by reading the section against `run_pre_push` and
  `run_ci`

## 4. Integration

- [ ] 4.1 Copy the new `scripts/guard.py` into a scratch clone of troupe at `origin/main`, turn its hooks on, and
  verify: a `docs:` commit changing a file under `protocol/schemas/` is refused naming it; the same change as `fix:`
  is made. Then run `uv run scripts/guard.py ci --base origin/main~50 --head origin/main --branch main` there and
  record what it reports in the pull request: history isn't refused after delivery, but it shows whether troupe has
  already shipped a schema change under a non-releasing type
- [ ] 4.2 Run `uv run scripts/check.py` and `openspec validate protocol-schema-commit-types --strict`, and verify both
  pass
- [ ] 4.3 After rebasing onto `origin/main`, run `uv run scripts/tofu.py plan` and verify it shows only
  `scripts/guard.py` updated in place in troupe and website. Keep it for the pull request

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #122`, the evidence from 1.4, 2.3, 4.1 and the plan
  from 4.3. CI must be green on all three OSes before the delivery is planned.
- Tick, archive and rebase onto main's state commit in one push, then ask once for the `plan-pr` approval.
- The owner merges by rebase and approves the `apply` job, which delivers `scripts/guard.py` to troupe and website.
  Confirm troupe's delivered file matches `main` here.
- Comment on #122 with the pull request and the archived change, check it's closed, and check its roadmap card says
  Done.
- Suggest to the owner that troupe's `contributing/releasing.md` point at the rule (and list `perf` and `revert`,
  which release too); that's troupe's change.
