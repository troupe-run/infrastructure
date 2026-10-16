# Design: declare the website's github-pages environment and its main-only deploy rule

## Context

See proposal.md for why. What shapes the approach:

- **Live state, read 2026-10-16** (`gh api repos/troupe-run/website/environments/github-pages`): created
  2026-10-07 by GitHub when Pages was set up; `can_admins_bypass: true`; one protection rule, `branch_policy`;
  `deployment_branch_policy: {protected_branches: false, custom_branch_policies: true}`; no reviewers, no wait timer.
  Its one deployment branch policy is `main` (type `branch`, ID `62248502`). It's the website's only environment.
- **The deploy job** (`website/.github/workflows/deploy.yml`) runs on `workflow_run` after CI completes on `main`,
  and uses `environment: github-pages` with `actions/deploy-pages`. A `workflow_run` run's ref is the default branch,
  so its deployment is made from `main` and passes the policy. Nothing in the website changes.
- **Precedents here:** `tofu/environments.tf` declares CI's `plan-pr`, `plan-main` and `apply` on infrastructure, and
  `tofu/release.tf` declares troupe's `release`. Each main-only one sets `custom_branch_policies = true`, adds one
  `github_repository_environment_deployment_policy` with `branch_pattern = "main"`, and sets
  `can_admins_bypass = false`.
- **Adopt before changing** (project constraint): import, prove a clean plan, then change.
- **The App can do it:** it already manages website's ruleset and labels, and its `administration: write`
  permission is what manages the CI environments today. Provider: integrations/github 6.13.0.
- **A sibling change** on branch `website-pages` (#51) declares the website's Pages settings in `repositories.tf`.

## Goals / Non-Goals

**Goals:**
- The environment, its branch policy and its bypass setting are declared, so any change to them on GitHub shows in
  the next plan (and the daily plan of `main`).
- No apply can delete the environment.

**Non-Goals:**
- Testing GitHub's refusal of an off-`main` deployment on the live repository. The same mechanism is what keeps
  `apply` and `release` main-only; ci-apply proved it on a throwaway repository (ci-apply tasks 2.3). Re-proving it
  here would mean pushing a branch to `website` that tries to deploy troupe.run.
- Reviewers or a wait timer on deploys. The website's pull requests are reviewed before they merge; a deploy on every
  push to `main` is the intent.

## Decisions

### D1. Declared in `environments.tf`, as its own two resources

The environment and its policy go in `tofu/environments.tf`, beside CI's, as `github_repository_environment.github_pages`
and `github_repository_environment_deployment_policy.github_pages_main_only`. The file's header widens from "the
environments that gate CI" to "the environments this repo declares", and its table gains a row for `github-pages`.

- Not folded into `local.ci_environments`: those carry the App's key and the state passphrase, and live on
  infrastructure. Mixing in a different repository would need a `repository` key on every entry and `moved` blocks
  for the three existing addresses, for no gain.
- Not in the `repository` module: only `website` has a Pages environment, and a module option for one caller is a
  second place to look.
- Not in `repositories.tf`: that's where #51 declares Pages, and two changes editing `repo_website`'s block at once
  would collide. The issue also names `environments.tf` as the model.

### D2. Adopt first, then tighten: two commits

1. Declare the environment exactly as it is live, `can_admins_bypass = true` included, with two `import` blocks in
   `tofu/imports.tf`: `website:github-pages` for the environment, and `website:github-pages:62248502` for the policy.
   The plan must show `2 to import, 0 to add, 0 to change, 0 to destroy`. Any change there means the declaration
   doesn't match GitHub, and is fixed before going on.
2. Set `can_admins_bypass = false`. The plan then shows the two imports and one in-place update of that one attribute.

The pull request carries both commits; its posted plan is step 2's. Splitting the adoption out keeps a mismatch in
the declaration from hiding inside the intended change.

### D3. `can_admins_bypass = false`

GitHub documents this setting as whether repository admins may bypass the environment's protection rules, and the
branch policy is one of them (`protection_rules: [{type: branch_policy}]`). The owner's login is an admin, and agents
share it (#47), so `true` leaves a route to deploy troupe.run past the branch rule that no plan would show. `false`
matches `apply`, `plan-main` and `release`, and the release-credentials spec's "no admin can bypass".

It can't lock the owner out: as admin, the owner can still change the environment on GitHub (the break-glass), and
the next plan shows it. `main`'s deploys don't depend on any bypass.

Whether `true` actually lets an admin deploy from another branch isn't verified, and needn't be: `false` is the
stricter value either way, and it costs nothing on `main`.

### D4. Everything else matches the live environment

`prevent_self_review = false`, no `reviewers` block, no `wait_timer`, `protected_branches = false`,
`custom_branch_policies = true`. These are what's live, so they import cleanly, and they're what the deploy needs.

### D5. `prevent_destroy` on the environment

If the declaration were removed, a plan would delete the environment. The next deploy would then fail, or, since a
job that names a missing environment makes GitHub create it with no protection, recreate it with no branch rule at
all: the exact hole #52 is about. `lifecycle { prevent_destroy = true }` makes such a plan fail instead, as the
repository module does for repositories. Taking it out of management on purpose needs a `removed` block, which leaves
the environment on GitHub.

The policy gets no `prevent_destroy`: deleting it alone leaves `custom_branch_policies = true` with no branches, so
nothing can deploy, which fails closed and shows in the plan.

## Risks / Trade-offs

- [The import IDs' format differs from what the provider expects] → the first plan fails or shows a create; step 1 of
  D2 catches it before anything changes. The formats are the provider's documented `<repo>:<environment>` and
  `<repo>:<environment>:<policy id>`.
- [GitHub resets the environment when Pages settings change, for example when #51 applies] → that shows as drift in
  the next plan (and the daily plan), and the apply restores it. Tasks recheck the environment after both applies.
- [Both changes are applied in either order] → they touch different resources and files; whichever merges second is
  rebased onto `main`'s state commit before its plan (memory: plan against current state).
- [`prevent_destroy` blocks a legitimate future removal] → the `removed` block is the documented route, and the
  comment says so.

## Migration Plan

1. The pull request's plan (after the owner approves its run) shows the two imports and the one in-place change.
2. The owner merges by rebase and approves `main`'s `apply` job.
3. Verify with `gh api repos/troupe-run/website/environments/github-pages` that `can_admins_bypass` is `false` and the
   branch policy is unchanged, and that the next deploy of the website's `main` succeeds.

Rollback: revert by pull request. Reverting step 2 sets `can_admins_bypass` back to `true`; reverting the whole change
needs a `removed` block (D5), so the environment stays on GitHub.
