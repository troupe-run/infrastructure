# Proposal

## Why

Each repository has GitHub features on that nobody uses (issues and Actions in `.github`), and some it should have
are off or set only by hand: discussions are off in troupe, private vulnerability reporting is off in infrastructure,
and the roadmap board isn't shown on infrastructure. A feature that's on where nobody looks collects issues,
discussions or workflows that are never seen. A feature set by hand drifts without anyone noticing (#136; owner,
2026-10-25).

## What Changes

- **Discussions on in troupe only.** `has_discussions` becomes a per-repository setting, true for troupe. Its
  categories are Q&A, Ideas and Announcements. The owner sets them by hand once, since no API can, and `oob.py`
  checks them for drift.
- **Questions go to troupe's discussions.** The org's issue chooser gets an "Ask a question" contact link to
  troupe's Q&A, and the contributing guide says to ask questions there rather than in an issue.
- **Issues off in `.github`.** Nothing is tracked there; org-wide work goes in infrastructure. The org's issue forms
  in `.github` still reach the other repositories.
- **Actions off in `.github`.** It has no workflows, and only the App changes its `main`. Actions is declared for
  all four repositories, so a change by hand shows in the plan.
- **Private vulnerability reporting on in all four.** The owner sets it to `enabled` in the "troupe-run baseline"
  code security configuration, which also covers repositories created later. The provider can manage neither, so
  `oob.py` checks the configuration and each repository's own setting.
- **Projects on in infrastructure.** The owner links the roadmap (project 1) to infrastructure, the declaration turns
  projects on there, like troupe and website, and `oob/projects.json` lists the link.
- **Members can't create Pages sites.** `tofu/org.tf` stops members creating public or private Pages sites. The
  website's site, which already exists, keeps serving and deploying.
- **Pull requests off in `.github`.** Only the App changes its `main`, through API commits, so a pull request
  there could never merge, and a fix to its files belongs in `org-profile/` here. The provider can't set it, so the
  owner turns it off by hand and `oob.py` checks it, with pull requests on everywhere else.
- **Sponsorships checked.** It's off in all four. GraphQL reads it, though the provider can't set it, so `oob.py`
  checks it stays off.
- **What can't be managed is noted.** The home page's Releases, Packages and Deployments panels have no API.
  They're listed as unmanaged in `oob/README.md`, with the reason. Forking can't be turned off for a public
  repository.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repositories`: each repository has only the features it uses (discussions in troupe only, no issues or Actions
  in `.github`, projects wherever the roadmap is linked), private vulnerability reporting is on everywhere, pull
  requests are off in `.github` only, Sponsorships is off everywhere, each checked out of band, and troupe's
  discussion categories are checked for drift.
- `org-settings`: members can't create Pages sites.
- `org-profile`: the issue chooser and the contributing guide send questions to troupe's discussions.

## Impact

- `tofu/modules/repository/` (new variables for discussions, issues and Actions, and the Actions permissions
  resource), `tofu/repositories.tf`, `tofu/org.tf`, `tofu/imports.tf`.
- `scripts/oob.py` and its tests, with new declarations in `oob/` and an updated `oob/projects.json`.
- `org-profile/.github/ISSUE_TEMPLATE/config.yml` and `org-profile/CONTRIBUTING.md`, delivered to `.github` by the
  plan.
- `oob/README.md`.
- Owner steps on GitHub before the merge: turn discussions on in troupe and set its categories, enable private
  vulnerability reporting in the baseline configuration, turn pull requests off in `.github`, and link the roadmap to
  infrastructure.
