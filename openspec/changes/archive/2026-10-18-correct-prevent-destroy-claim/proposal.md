# Proposal

## Why

Three places say that removing a repository's declaration makes the plan fail on `prevent_destroy`: README.md's "An
apply can't delete a repository", the comment on `github_repository.this` in `tofu/modules/repository/main.tf`, and
the repositories spec's scenario "Removing a declaration doesn't delete the repository". That holds only while the
`module "repo_<name>"` block is still there (`count = 0`, a forced replacement). Deleting the block deletes its
`prevent_destroy` with it, and the plan then destroys the repository. #61 found the same flaw for `github-pages`, and
the owner chose to fix the repository case separately (#85, 2026-10-18).

The flaw matters because it points the reader at the wrong gate. What actually stops a repository being lost is the
owner reading the plan before approving it, with `archive_on_destroy = true` as the backstop: an approved destroy
archives the repository instead of deleting it.

## What Changes

- README.md's "An apply can't delete a repository" says what `prevent_destroy` refuses (a destroy while the block is
  still declared), what it doesn't (deleting the block), that such a plan shows the repository being destroyed, and
  that `archive_on_destroy` archives it rather than deleting it. It also names what an approved destroy does lose
  before the archive: the module's other resources in that repository, such as its labels and Dependabot settings.
- The comment on `github_repository.this` in `tofu/modules/repository/main.tf` says the same in one place, pointing
  at README.md.
- The repositories spec's requirement "An apply never deletes a repository" stops claiming the plan refuses a removed
  declaration. It keeps the promise that matters (no apply deletes a repository) and says how each way of removing
  one behaves: a `removed` block forgets it, a destroy the block still declares is refused, and a deleted block
  plans a destroy that archives it.
- The `archive_on_destroy` claim is proven once on a throwaway `troupe-run/infra-probe-*` repository before the
  README states it, because nothing here has exercised it yet.

Out of scope: a check-time test, like #61's for environments, that fails `scripts/check.py` when a managed
repository's declaration disappears. It's a possible follow-up if the owner wants one.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repositories`: "An apply never deletes a repository" no longer says a removed declaration fails the plan. It says
  which removals are refused, forgotten or archived.

## Impact

- `README.md`, `tofu/modules/repository/main.tf` and `tofu/probe/main.tf` (comments only),
  `openspec/specs/repositories/spec.md`.
- No change to any resource: the plan is unchanged.
- A throwaway repository is created and deleted for the probe. It needs the owner to install the infrastructure App
  on it and to approve the `op` prompts.
