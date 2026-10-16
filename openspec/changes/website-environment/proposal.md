# Proposal: declare the website's github-pages environment and its main-only deploy rule

## Why

troupe.run is deployed by the website's `deploy` job through the `github-pages` environment, and only that
environment's branch policy stops a run on another branch from deploying. GitHub created the environment when Pages
was set up, and nothing here declares it, so if the policy were removed or widened, any branch could deploy to
troupe.run and no plan would show it (#52). The environment also lets admins bypass its rules today, which the
environments declared for CI and for troupe's releases don't allow.

## What Changes

- `tofu/environments.tf` declares the website's `github-pages` environment and its one deployment branch policy,
  `main`, in the same shape as `apply`, `plan-main` and troupe's `release`: custom branch policies only, no
  reviewers, no wait timer.
- Both are imported, not created (`website:github-pages`, and the policy's ID, `62248502`). The first plan proves
  the adoption: two imports and nothing else.
- Then `can_admins_bypass` goes from `true` (GitHub's default when it created the environment) to `false`, so no admin
  can deploy past the branch rule. That shows as one in-place change.
- The file's header says it now holds the website's deploy environment as well as CI's.

Out of scope: the website's Pages settings themselves (source, custom domain, HTTPS), which are #51 and change
`repositories.tf`; `deploy.yml`, which already names `github-pages` and runs only on `main`; the website's DNS (#55).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repositories`: adds "The website deploys from main only". The `github-pages` environment allows only `main` to
  deploy, no admin can bypass it, and a change made on GitHub shows in the next plan.

## Impact

- `tofu/environments.tf`: two new resources on `website`, adopted by import.
- `tofu/imports.tf`: two import blocks.
- An apply, after the owner approves its plan, changes one setting on GitHub: `github-pages`' `can_admins_bypass`
  becomes `false`. The branch rule, the deploy job and the live site don't change.
- The infrastructure App already manages `website` (its ruleset and labels), so it needs no new permission or
  installation.
