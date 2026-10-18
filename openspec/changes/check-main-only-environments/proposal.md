# Fail the check when a main-only environment's declaration is removed or weakened

## Why

Four environments must only ever be reachable from `main`: infrastructure's `plan-main` and `apply`, troupe's
`release`, and the website's `github-pages`. If a declaration is deleted, OpenTofu destroys the environment, and the
next job that names it makes GitHub recreate it with no branch rule and no reviewer. website-environment (#56) put
`prevent_destroy` on `github-pages` and claimed that stops such a plan (its design D5). It doesn't: with the block
deleted, the plan said `2 to destroy` and nothing refused it, because `prevent_destroy` goes with its block.
Environments have no `archive_on_destroy`-style backstop, so today the only thing that catches this is the owner
reading the plan (#61).

## What Changes

- **A new test in `scripts/tests/`**, run by `scripts/check.py`, fails when any of the four environments:
  - is no longer declared;
  - is no longer limited to `main`: its deployment branches aren't custom policies, or follow protected branches, or
    its branch policies aren't exactly the one pattern `main`;
  - lets admins bypass it.
  
  For `apply` it also fails if the owner is no longer its required reviewer, since a recreated `apply` would lose that
  too (#61). The expected environments are listed in that one test, so removing one means changing the test in the
  same diff, before any plan exists.
- **The test reads the declarations as text**, as `test_required_checks.py` does, and refuses a declaration shape it
  doesn't recognise rather than guessing (design D2).
- **The comment on `github_repository_environment.github_pages`** in `tofu/environments.tf` is corrected:
  `prevent_destroy` refuses a destroy only while the block is there, and this test is what catches the block being
  deleted. `prevent_destroy` stays.

Out of scope:

- **`plan-pr`.** It runs on any branch by design, so it isn't main-only. Its owner approval isn't covered here.
- **A plan-level guard in CI.** The owner chose a check-time test instead (2026-10-16, in the #52 session).
- **README.md's "An apply can't delete a repository"** says removing a repository's declaration fails on
  `prevent_destroy`. Deleting the `module` block deletes that guard too, as for environments. The repository's
  `archive_on_destroy` is the real backstop there. This change doesn't fix that sentence: #85 tracks it.
- **`prevent_destroy` on `ci` or `release`.** The owner chose not to add it (2026-10-18, design).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: "Only main can apply" gains a scenario. Removing or weakening the declaration of `plan-main` or `apply`
  fails `scripts/check.py`.
- `release-credentials`: "The release key is readable from main only" gains the same scenario for `release`.
- `repositories`: "The website deploys from main only" gains the same scenario for `github-pages`.

## Impact

- New `scripts/tests/test_main_only_environments.py`, marked `tofu`. It reads `tofu/environments.tf` and
  `tofu/release.tf`, which are already in that scope in `scripts/check-paths.toml`.
- `tofu/environments.tf`: comments only. No resource changes, so the pull request's plan should read `No changes.`
- No change to the org, its secrets or the workflows.
