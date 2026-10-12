# Tasks

## 1. Probe on a throwaway repository (design D8)

- [ ] 1.1 Give the module what the probe needs, and leave the live repositories unchanged:
  - `required_checks`: a list of `{ context, integration_id }`, defaulting to `[]`, which adds a
    `required_status_checks` rule (`strict_required_status_checks_policy = false`, D3) only when it isn't empty;
  - `main_ruleset` (`pull-request` | `app-only` | `none`, default `pull-request`) in place of `protect_main`, with the
    `app only` ruleset (D4). `repo_github` gets `none` for now, and a `moved` block is added if the ruleset's address
    changes.

  Verify:
  - `scripts/check.py` passes;
  - a local plan of the live root shows no changes.
- [ ] 1.2 Create `troupe-run/infra-probe-<yyyymmdd>` (public, with a README), and have the owner add it to the
  `troupe-run-infrastructure` App's installation. Give it a `probe-check` workflow: one job on `pull_request`, which
  passes unless the commit holds `fail.txt`. Also add a second job, skipped by `if: false`. Point `tofu/probe` at it
  with `probe_main_ruleset` and `probe_required_checks` (both checks). Verify: `tofu plan` in `tofu/probe` shows the
  probe repository with the `pull-request` ruleset and both checks required.
- [ ] 1.3 Run D8 steps 1–5. For each, record the command and GitHub's response:
  - a red pull request is refused;
  - `--admin` merges it;
  - a status posted with the owner's token doesn't satisfy the check;
  - the skipped job counts as passed;
  - the App's file commit to `main` is accepted despite the required check.

  Verify: all five behave as the rulesets spec delta says. Any surprise stops the change and is raised with the owner.
- [ ] 1.4 Run D8 step 6 with `probe_main_ruleset = "app-only"`. Verify:
  - the owner's push is refused;
  - the owner's pull request merge is refused, with `--admin` too;
  - the App's file commit is accepted.
- [ ] 1.5 Run D8 step 7. Save `gh api repos/troupe-run/<probe>` before and after applying the D5 settings, and diff
  the two. Verify: only `allow_merge_commit`, `allow_squash_merge`, `delete_branch_on_merge`, `has_wiki`,
  `has_projects` and `updated_at`/`pushed_at` differ.
- [ ] 1.6 Run D8 step 8 with a throwaway org project linked to the probe repository and holding one of its issues.
  Set `has_projects = false`. Verify, and record which way D5 goes for `troupe`:
  - the link and the item survive (`gh api graphql` on the project's `repositories` and `items`);
  - the repository's linked-projects list still shows it.
- [ ] 1.7 Record the findings in design.md (under D8, as ci-apply did) and in the adopt-org findings memory. Then
  delete the probe repository and the throwaway project, and remove the probe's local state, `terraform.tfvars` and
  workflow file. Verify:
  - `gh repo view troupe-run/<probe>` reports not found;
  - `uv run scripts/oob.py` reports no project difference;
  - `git status` shows no probe leftovers.

## 2. Required checks (design D1, D3)

- [ ] 2.1 Add PyYAML and `types-PyYAML` to the `dev` dependency group, and run `uv lock`. Verify: `uv sync --locked`
  succeeds, and `scripts/guard.py` still imports nothing outside the standard library (`test_guard_*` still pass).
- [ ] 2.2 Write `tofu/required-checks.json` with the names in design.md's Context table, for `infrastructure`,
  `troupe` and `website`. In `repositories.tf`, map App slugs to IDs, and pass each repository's list to the
  module's `required_checks` (task 1.1). Verify:
  - `scripts/check.py` passes;
  - a local plan shows `required_status_checks` added to exactly the three `protect main` rulesets, with the
    expected names and IDs.
- [ ] 2.3 Write `scripts/tests/test_required_checks.py` (D1). It expands every `pull_request` job's name across its
  matrix (`include`/`exclude`) in `ci.yml`, `guard.yml` and `tofu.yml`, leaving out `changes`. It asserts that the
  result equals `infrastructure`'s `github-actions` entries, and that `DCO` is listed. Name each test for what its
  body checks. Verify the test fails when it should:
  - temporarily renaming a matrix leg in a scratch copy fails it, and so does dropping an entry from the JSON;
  - the real files pass.
- [ ] 2.4 Update the docs:
  - the README's "How main is protected": the required checks, where their names live, and that the owner's bypass
    merges past a red check;
  - `docs/development-workflow.md`: the `guard` check *is* required now (lines 17, 27–28 and 90), and the
    `required-checks` references become present tense;
  - the comment in `.github/workflows/guard.yml` (line 7). It is delivered, so troupe gets the change through the
    plan.

  Verify:
  - `scripts/check.py` passes;
  - `grep -rn "once .required-checks" docs README.md .github` finds nothing.

## 3. The PR plan as a required check (design D2)

- [ ] 3.1 Write `scripts/plan_needed.py` (standard library only, `mypy --strict`). It takes the changed paths on
  stdin, prints `plan=true|false`, and the ignore-list lives in it. Write `scripts/tests/test_plan_needed.py`:
  - every path OpenTofu reads (the `file(`/`fileset(` paths in `tofu/*.tf`, `guard_files` from `guard_delivery.tf`,
    `org-profile/**`) plans;
  - a docs-only list doesn't plan;
  - a mixed list plans;
  - an empty list plans;
  - `docs-old/x` plans (prefix, not substring).

  Verify: the tests pass, and the first one fails when `.claude/` is added to the ignore-list.
- [ ] 3.2 Add the `changes` job to `tofu.yml`, and make `pr-plan` depend on it with D2's condition. Add
  `plan (pull request)` to `infrastructure`'s entries in `required-checks.json`. Verify:
  - `scripts/check.py` passes, including `test_required_checks.py`;
  - `actionlint` passes, if it can be run with `uvx` or `brew`; otherwise say so.
- [ ] 3.3 Update the README's "Changing the org": a pull request that changes nothing OpenTofu reads skips the plan
  and asks for no approval, and every other pull request can't merge until its plan has run. Verify:
  - `scripts/check.py` passes;
  - this change's own pull request (which changes `tofu/`) asks for the plan approval, and a scratch commit touching
    only `openspec/` is shown by `plan_needed.py` to skip.

## 4. `.github`'s ruleset and notes (design D4, D6)

- [ ] 4.1 Set `repo_github` to `main_ruleset = "app-only"` (task 1.1), with the App's bypass. Update the README
  ("Adding a repository", which still names `protect_main`, and "How main is protected"). Verify:
  - `scripts/check.py` passes;
  - a local plan shows one ruleset created on `.github` with only the App as a bypass actor, and no other ruleset
    replaced.
- [ ] 4.2 Add the D6 note as the first line of each file in `org-profile/`. Verify:
  - a local plan shows four `github_repository_file.org_profile` updates, each with a new `chore: sync ...` message;
  - after the apply, the org profile page renders without the note (checked in follow-up).

## 5. Repository settings and the plan App (design D5, D7)

- [ ] 5.1 Change the module's defaults per D5. Set `has_projects = true` on `troupe` with a comment, if and only if
  task 1.6 found that turning it off affects the linked project. Remove the `variables.tf` comment that calls the
  defaults findings. Verify:
  - `scripts/check.py` passes;
  - a local plan shows, per repository, only the D5 fields changing.
- [ ] 5.2 The owner deletes `troupe-run-infrastructure-plan` (D7) and its 1Password item. Then remove it from:
  - `oob/app-installations.json`;
  - `oob/README.md`'s table;
  - `tofu/probe/main.tf`'s comment.

  Verify: `uv run scripts/oob.py` reports no difference, and `grep -rn "infrastructure-plan"` outside `archive/`
  finds nothing.

## 6. Land it

- [ ] 6.1 Open the pull request (`Closes #14`). Its evidence:
  - the CI plan comment, after the owner approves the run. It must show only the changes listed in design.md's
    Migration step 3;
  - `scripts/oob.py`'s output;
  - the probe's findings.

  Verify: every check is green, and the plan comment is present and matches.
- [ ] 6.2 Comment the owner's four decisions of 2026-10-12 on #14, and link the comment from the proposal. The four
  decisions are:
  - delete the plan App;
  - require the PR plan, skipped by a job condition;
  - list the matrix names;
  - no owner bypass on `.github`.

  Verify: the comment URL.
- [ ] 6.3 Open a follow-up issue for refusing `gh pr merge --admin` in Claude Code sessions (design, Risks), and the
  open question of DCO on `website`. Verify: the issue URLs.

## Workflow follow-up

- Archive on the branch before the merge (`/opsx:archive`), syncing the `rulesets`, `ci-apply`, `repositories`,
  `org-profile` and `teams-and-access` specs.
- After the owner merges, check the first apply. Report the run links.
  - The `tofu` run plans exactly the reviewed changes, waits for the owner, and applies.
  - The App's state commit lands on `main` under the new ruleset, and no second plan follows.
  - The rulesets read back with the required checks, and `.github` has its `app only` ruleset.
  - The org profile page renders without the note.
  - A manual `gh workflow run tofu.yml` reports no changes.
- The next docs-only pull request shows `plan (pull request)` as skipped and merges without an approval. The next
  pull request that changes `tofu/` waits for its plan.
- Comment on #14 and close it, and tick `required-checks` on #1.
