# Design

## Context

See proposal.md for why. The facts the approach rests on:

- Each managed repository is a `module "repo_<name>"` call in `tofu/repositories.tf`. The module
  (`tofu/modules/repository/main.tf`) holds `github_repository.this` (`archive_on_destroy = true`, `prevent_destroy`)
  and, in the same repository, `github_issue_labels.this`, `github_repository_vulnerability_alerts.this`,
  `github_repository_dependabot_security_updates.this` (both `prevent_destroy`), a `main` or `app_only` ruleset, and
  `github_repository_pages.this` for the website (`prevent_destroy`).
- `prevent_destroy` refuses a destroy only while its block is in the configuration (#52, #61). adopt-org's probe
  (design D7, 2026-10-11) "removed the declaration" with `count = 0`, which keeps the block, so it proved the refusal
  but never tested deleting the block. Its `removed` block step planned `0 to destroy, 3 to forget`.
- With the block deleted, the provider destroys from state alone. Whether the repository is archived depends on the
  `archive_on_destroy` recorded in state, not on the configuration, which is gone. adopt-org's import apply wrote it
  to state (`1 changed`, the provider-local attributes). Nothing has run an archiving destroy yet.
- Deleting a live `module "repo_<name>"` block also means deleting its `import` blocks in `tofu/imports.tf` and
  every reference elsewhere (`environments.tf`, `guard_delivery.tf`), or `tofu validate` fails. That gets in the way
  of a careless edit, but it isn't a gate: the same edit removes them.
- `tofu/probe/` points the same module at a throwaway repository, with its own git-ignored, encrypted state. Its
  `declared` variable is the `count = 0` step.

## Goals / Non-Goals

**Goals:**

- Every statement about removing a repository, in README.md, the module's comment and the repositories spec, is one
  that a probe has shown on the current provider (`integrations/github ~> 6.13`).
- README.md tells the owner what to look for in a plan before approving it, what an approved destroy loses, and how
  to get the repository back.

**Non-Goals:**

- No change to any resource or to the live plan. The module's `prevent_destroy` and `archive_on_destroy` stay as they
  are: both are still right, they just protect less than the README claims.
- No check-time test that fails when a managed repository's declaration disappears (proposal: out of scope).
- The `removed` block route isn't probed again. adopt-org proved it, and this change doesn't touch it.

## Decisions

### D1. Prove the archive on a throwaway repository before the README claims it

The README will tell the owner that an approved destroy archives the repository, and nothing here has ever done one.
The probe runs in `tofu/probe/` against `troupe-run/infra-probe-<date>`, because it uses the same module as the live
repositories:

1. Create the repository with `gh repo create --public --add-readme`. The owner adds it to the infrastructure App's
   installation. Open an issue on it and give it one label the module manages (`bug`, from
   `labels/github-defaults.json`), so the probe shows what happens to a label's assignments.
2. `tofu apply` with `declared = true`, which imports the repository and its labels and creates the ruleset and the
   Dependabot settings. Then plan again, which must be clean.
3. Plan with `declared = false` (`count = 0`). It must fail on `prevent_destroy`, naming the repository. This
   re-checks the spec's "refused" scenario on today's provider.
4. Delete the `module "probe"` block and the two `import` blocks that target it, as an uncommitted edit. Plan, and
   record the destroy list. Apply it.
5. Record the repository's state on GitHub: `archived`, its labels, the issue's labels, its rulesets, and whether
   Dependabot alerts are on.
6. Unarchive it with `gh repo unarchive`, restore `main.tf` with `git checkout`, and apply with `declared = true`
   again, to show how a repository is recovered and that the plan is then clean.
7. Delete the repository, the probe's state and `terraform.tfvars`.

Step 4's edit is never committed. A committed variant (a second file to move away, say) would make the probe
repeatable, but it adds code that exists only for this probe. The probe's header comment describes the edit instead,
as it does for the other probes.

*Alternative:* a scratch root module in the scratchpad. It would leave `tofu/probe/main.tf` untouched, but it's a
second copy of the probe's provider and encryption setup that nobody can find to run it again.

### D2. Check that the live state records `archive_on_destroy`

The backstop is read from state, so the claim holds only for repositories whose state says
`archive_on_destroy = true`. A read of the live state (`uv run scripts/tofu.py state show
module.repo_<name>.github_repository.this`) for each of the four repositories confirms it. This is a read only. If
any of them says otherwise, stop and ask the owner: a clean plan would mean the attribute isn't being compared, and
the README can't make its claim for that repository until it's fixed.

### D3. The README says what the plan shows, not what stops it

README.md's paragraph becomes, in substance:

- `prevent_destroy` refuses a plan that would destroy a repository whose `module` block is still there, for example
  one switched off or replaced.
- Deleting the block deletes the guard with it. The plan then lists the repository and its resources as destroyed,
  and only the owner reading it stands between that plan and an apply.
- If it's applied anyway, `archive_on_destroy` archives the repository rather than deleting it. What the apply has
  already destroyed in that repository first is lost: the probe's step 5 says which of labels (and their assignments
  on issues and pull requests), the ruleset, and Dependabot alerts and security updates.
- To get it back: unarchive it, restore the declaration and its `import` blocks, and apply. The apply recreates what
  was destroyed.
- The `removed` block, unchanged, is the way to stop managing a repository.

The wording follows the probe's results. If a step shows something else (the repository is deleted, or labels
survive), the README says what was shown, and the spec delta is corrected before archive.

### D4. The module's comment points at the README

The comment on `github_repository.this` says in two lines what each setting does (`prevent_destroy` refuses a
destroy while this block exists; `archive_on_destroy` archives the repository when the block is deleted) and points
at README.md for the rest. The comment on the Dependabot resources already says that deleting a block gets past
`prevent_destroy`, and stays.

### D5. The spec stops promising that no repository is archived

The current requirement says no plan or apply SHALL "delete or archive" a repository, and its scenario says a removed
declaration is refused. Neither was ever true for a deleted block, so the delta corrects the promise rather than
weakening a working one. It keeps "never deletes", which the probe will show, and states the three removals
separately (specs/repositories/spec.md).

## Risks / Trade-offs

- [The probe shows the repository deleted, not archived] → Then the README must not claim the backstop, and the
  module has a real gap. Stop, delete the probe, and bring the result to the owner before writing anything.
- [Deleting `github_issue_labels` removes the labels from every issue, and unarchiving doesn't restore them] → The
  probe measures it, and the README names it as the loss an approved destroy causes. Nothing here prevents it: the
  owner reading the plan does.
- [The archiving apply fails partway, for example archiving before a dependent resource is destroyed] → The probe
  records the error and the repository's state, and the README describes what really happens. It's a throwaway, so a
  half-applied state is just deleted with it.
- [Step 4's uncommitted edit is committed by mistake] → It's restored with `git checkout` in step 6, and the task
  checks `git status` is clean before the next commit.
- [The probe needs the owner] → Adding the repository to the App's installation and the `op` prompts are the owner's.
  The task says so up front, so the run waits for them instead of failing halfway.

## Migration Plan

Nothing to migrate. The pull request's plan must read `No changes.`, because only a comment and documentation change.
