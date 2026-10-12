# Proposal

Issue: #6 (part of #1). The owner's decisions of 2026-10-12 are recorded in #6's comments and in design.md.

## Why

Every plan and apply runs on the owner's Mac through `op`, and needs Touch ID within about a minute. Several applies
in `development-workflow` stalled on that timeout, and every pull request's plan is pasted by hand. The brief always
said that applies run from GitHub Actions, only from `main`, through an environment that needs the owner's approval.
`adopt-org` deferred that, and `development-workflow` deliberately went first so it could be debugged locally. Now
it's next on #1, and every later change (`required-checks`, `capability-labels`) gets cheaper with it.

## What Changes

- **A `tofu` workflow** on this repository:
  - **on a pull request**, it plans against `main`'s state and posts the plan on the pull request as its evidence;
  - **on a push to `main`**, it plans, shows the plan, waits for the owner's approval through the `apply`
    environment, and applies exactly that saved plan;
  - **after an apply**, it commits the new encrypted state to `main` as the App;
  - when a plan has no changes, it stops without asking for approval;
  - it can be re-run by hand on `main`, for example after drift.
- **Two environments on this repository, declared in OpenTofu:**
  - `apply`: the owner is a required reviewer, and only `main` may deploy to it. It holds the write App's key.
  - `plan`: no reviewer. It holds a read-only App's key, so a pull request can be planned unattended.
- **A second, read-only GitHub App** (`troupe-run-infrastructure-plan`) for plans. The owner creates and installs it
  by hand, and `oob/app-installations.json` records its permissions. A pull request that changes the workflow can at
  most read the org and decrypt the state, never change anything.
- **State stays committed on `main`.** There is no GitHub-native state backend, and the owner doesn't want a new
  service for it. So the infrastructure App gets the same push bypass on this repository's ruleset that it has on
  troupe's, and only uses it to commit state.
- **The App's key is supplied per run, not saved in the plan.** The App's identity becomes ephemeral input, so a plan
  made with the read-only App can be applied with the write App.
- **Secret values are set by the owner** from 1Password straight into `gh secret set`, so they never appear on
  screen or in a session. OpenTofu still never manages secret values.
- **`scripts/tofu.py` stays the single entry point**, locally and in CI.
- **Local applies become the break-glass,** documented in the README. They still work as before.

Out of scope:
- a scheduled drift plan;
- making the `tofu` plan a required check (`required-checks`);
- state locking beyond serialising the workflow's own runs.

## Capabilities

### New Capabilities

- `ci-apply`: how a declared change reaches the org from CI:
  - the plan on every pull request;
  - the plan, approval and apply on `main`;
  - the environments that gate them;
  - the read-only plan identity;
  - the state commit after an apply.

### Modified Capabilities

- `state-and-apply`:
  - The state is committed to `main` by CI after each apply, no longer on the change's branch.
  - "The tool acts as the infrastructure App" allows the read-only plan App for plans.
  - A pull request's plan evidence comes from CI.
- `rulesets`: the App's push exception extends to this repository, for committing state only.

## Impact

- **New:**
  - `.github/workflows/tofu.yml`;
  - `tofu/environments.tf` (both environments and the `main`-only deployment policy);
  - a probe experiment in `tofu/probe` for the ephemeral App identity.
- **Changed:**
  - `tofu/providers.tf`: the App ID, installation ID and key become ephemeral variables, defaulting to the write App.
  - `tofu/modules/repository`: `delivery_app_id` becomes a general App push bypass.
  - `tofu/repositories.tf`: the bypass is set on infrastructure.
  - `scripts/tofu.py`, if the ephemeral variables need it.
  - `oob/app-installations.json`;
  - `README.md`, `CLAUDE.md` and the org's `CONTRIBUTING.md`: the plan comes from CI, and applying locally is the
    break-glass.
- **GitHub:**
  - the two environments and their secrets;
  - a bypass entry on infrastructure's ruleset;
  - a new App and its installation;
  - App commits of `tofu/terraform.tfstate` to `main`.
- **The owner,** by hand:
  - creates and installs the plan App;
  - stores its key in 1Password;
  - sets six environment secrets, from 1Password.
