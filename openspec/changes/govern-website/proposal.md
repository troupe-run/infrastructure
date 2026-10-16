# Proposal: govern the website with the org workflow and the guard, without DCO

## Why

`troupe-run/website` is the only active repository the development workflow doesn't cover (#54). None of its 54
commits on `main` is a Conventional Commit, it has no OpenSpec, it has never had an issue, and nothing stops an agent
committing straight to a branch with no change behind it. troupe and this repository are governed by the guard; the
website should be too. It keeps two differences, both decided by the owner on 2026-10-16: it takes no DCO sign-off
(its CONTRIBUTING.md accepts contributions under MIT and CC BY 4.0 with no separate agreement), and it has no release
process (it deploys on every merge to `main`).

## What Changes

- **The website receives the guard.** `website` joins `guard_targets` in `tofu/guard_delivery.tf`, so the App
  delivers the guard's eight files (seven sources and `.github/guard-delivery.json`) straight to its `main`, as it
  does to troupe. Delivery waits for the website's ruleset as well as troupe's.
- **The App may push the deliveries.** `repo_website` sets `app_bypass_id`, so its `protect main` ruleset lets the
  infrastructure App push to `main`. Nothing else about the ruleset changes: everyone else, the owner included, still
  reaches `main` only by a rebase-merged pull request.
- **The guard's check is required.** `guard (workflow rules)` joins `test` in the website's entry in
  `tofu/required-checks.json`. DCO does not: it stays required on troupe and this repository only, and the DCO App is
  not installed on the website.
- **The roadmap is linked.** `repo_website` sets `has_projects = true`, with the same reason as troupe's, and the
  owner links project 1 to the website (`gh project link` is owner-only in the guard). `oob/projects.json` declares
  which repositories the roadmap is linked to, and `scripts/oob.py` reports a difference, since OpenTofu can't
  manage project links.
- **Words that say "troupe" where they mean "every governed repository"** are widened: the `development-workflow`
  spec's Purpose, the README's "Delivering the guard", and its stop-delivering steps.

**Prerequisite, in the website (not this repository):** before this change's plan is applied, the website's own pull
request must have merged `openspec/`, `scripts/check.py` (wrapping its CI's npm steps), `scripts/check-paths.toml`
and its contributor docs (uv, the workflow, no DCO, how an outside fix is taken in). That pull request goes through the website's own checks,
because only the guard's files may arrive by delivery. It has its own issue in the website repository.

**Outside contributions:** the website's **Improve this page** pull requests (from GitHub's web editor, on a fork)
will fail the newly required `guard` check. A maintainer carries each one through the workflow and credits its
author, and the website's CONTRIBUTING says so (owner, 2026-10-16; design D8).

Out of scope:
- Rewriting the website's existing history to Conventional Commits: decided against (owner, 2026-10-16; design D7).
- A release process for the website (decided: none).
- The website's Pages settings (#51, `website-pages`), its `github-pages` environment (#52, `website-environment`)
  and its DNS (#55). They touch the same module and spec, so whichever merges second rebases.
- Turning on Dependabot and secret scanning (#53).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `guard-delivery`: a new requirement naming the repositories that receive the guard (troupe and the website), and
  that a repository receives it only once it holds what the guard needs to run.
- `rulesets`: "Each repository requires its own checks" gives the website the `guard` check alongside its CI test,
  and says DCO isn't required there.
- `repositories`: "Unused features are off" keeps the roadmap linked to the website as well as troupe.
- `org-settings`: "Issue types and the org project are checked for drift" also covers which repositories the org's
  project is linked to.

## Impact

- `tofu/guard_delivery.tf`: `guard_targets` gains `website`; `depends_on` gains `module.repo_website`.
- `tofu/repositories.tf`: `repo_website` gains `app_bypass_id` and `has_projects = true`.
- `tofu/required-checks.json`: the website's entry gains `guard (workflow rules)`.
- `oob/projects.json`, `scripts/oob.py` and its tests: the roadmap's linked repositories.
- `README.md`, `openspec/specs/development-workflow/spec.md` (Purpose): troupe-only wording.
- On GitHub, after the owner approves the plan: the website's ruleset gains the App as a bypass actor and the
  `guard` check, projects turn on, and eight commits by the App land on the website's `main`. Each push to `main`
  runs the website's CI and deploy, so the unchanged site is redeployed up to eight times.
- The infrastructure App is already installed on the website (it manages its ruleset and labels). Its permissions
  already cover delivering a workflow file (`workflows: write`), as they do for troupe. The installation's repository
  list is confirmed by hand (teams-and-access).
