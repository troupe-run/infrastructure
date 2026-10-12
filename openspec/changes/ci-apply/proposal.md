# Proposal

Issue: #6 (part of #1). The owner's decisions of 2026-10-12 are recorded in design.md and on #6:
[state and the first PR-plan choice](https://github.com/troupe-run/infrastructure/issues/6#issuecomment-6115909893),
[approval-gated PR plans instead](https://github.com/troupe-run/infrastructure/issues/6#issuecomment-6117082829).

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
- **Three environments on this repository, declared in OpenTofu,** each holding the App's key, the passphrase and
  the billing email:
  - `plan-pr`: any branch, and the owner approves each run. A pull request's plan waits for one click.
  - `plan-main`: `main` only, with no reviewer. The plan after a merge runs unattended.
  - `apply`: `main` only, and the owner approves.
- **The read-only App was tried and set aside.** The owner first chose a second, read-only App for PR plans
  (`troupe-run-infrastructure-plan`, created 2026-10-12). The probe showed it can't read repositories' merge settings,
  so its plans would show false changes on every repository. The owner then chose approval-gated PR plans with the
  one App. The read-only App stays declared in `oob/`, unused, until `required-checks` decides its fate.
- **State stays committed on `main`.** There is no GitHub-native state backend, and the owner doesn't want a new
  service for it. So the infrastructure App gets the same push bypass on this repository's ruleset that it has on
  troupe's, and only uses it to commit state.
- **The App's key is supplied per run, never saved in a plan:** it becomes ephemeral input.
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
  - the state commit after an apply.

### Modified Capabilities

- `state-and-apply`:
  - The state is committed to `main` by CI after each apply, no longer on the change's branch.
  - A pull request's plan evidence comes from CI.
  - A saved plan holds no key.
- `rulesets`: the App's push exception extends to this repository, for committing state only.

## Impact

- **New:**
  - `.github/workflows/tofu.yml`;
  - `tofu/environments.tf` (the three environments and their `main`-only deployment policies);
  - probe experiments in `tofu/probe` for the ephemeral key and the environments.
- **Changed:**
  - `tofu/providers.tf`: the App's key becomes an ephemeral variable.
  - `tofu/modules/repository`: `delivery_app_id` becomes a general App push bypass.
  - `tofu/repositories.tf`: the bypass is set on infrastructure.
  - `oob/app-installations.json`;
  - `README.md`, `CLAUDE.md` and the org's `CONTRIBUTING.md`: the plan comes from CI, and applying locally is the
    break-glass.
- **GitHub:**
  - the three environments and their secrets;
  - a bypass entry on infrastructure's ruleset;
  - a read-only App and its installation (created, then set aside);
  - App commits of `tofu/terraform.tfstate` to `main`.
- **The owner,** by hand:
  - created and installed the read-only App (done, now unused);
  - sets nine environment secrets, from 1Password;
  - approves each PR plan run, and each apply.
