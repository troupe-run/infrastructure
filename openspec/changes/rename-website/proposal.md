# Proposal

Issue: #4 (part of #1).

## Why

The website repository is the only one not named for what it is: `troupe-run.github.io`, beside `troupe`, `.github`
and `infrastructure`. That name only matters for a site served at `https://troupe-run.github.io/`. Ours is a
workflow-built Pages site on the custom domain `troupe.run`, which a project site can carry just as well. So it
can be `website`, and https://troupe.run keeps serving.

The issue's one blocker has already gone. It was the stale `.github` sync message from `adopt-org`, which
`development-workflow` fixed: every sync commit now names its content hash.

## What Changes

- **The repository is renamed to `website`** through OpenTofu (`tofu/repositories.tf`), applied by CI after the
  owner approves the plan. This is the first change to reach the org through `ci-apply`. Its state commit is the
  first live run of `scripts/commit_state.py`.
- **The plan:**
  - the repository is renamed in place;
  - its "protect main" ruleset is updated in place, so it's never unprotected;
  - its labels resource is **replaced**, because its `repository` attribute forces it. The ten default labels are
    deleted and created again, with the same names and colours. No issue or PR in the repository carries a label
    today, so nothing is lost (design D2).
- **This repository's references to the old name:**
  - `tofu/` (the module and the import IDs);
  - `oob/README.md`;
  - `org-profile/CONTRIBUTING.md`, synced into `.github` with the content-hash message;
  - the `repositories` and `rulesets` specs;
  - a guard test's example repository.
- **A pull request into the website repository** for its own references: `README.md`, `astro.config.mjs`'s
  `editLink`, and the footer's "Site source" link. It merges after the rename. Its deploy then republishes the
  site from the renamed repository.
- **The site is checked after the rename and again after that deploy:**
  - Pages keeps `cname: troupe.run` and HTTPS enforced;
  - https://troupe.run answers 200;
  - https://www.troupe.run redirects to it.
- **The local folder** `~/Projects/troupe/troupe-run.github.io` becomes `~/Projects/troupe/website`.

Out of scope:
- archived OpenSpec changes and historical docs that name the old repository, including the website repository's own
  `docs/superpowers/` plans. They stay as history, and GitHub redirects the old URLs.
- DNS: its records point at `troupe-run.github.io` and GitHub's IPs, which stay valid for a project site.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repositories`: the managed repositories are `troupe`, `.github`, `infrastructure` and `website`.
- `rulesets`: the protected repositories are `troupe`, `infrastructure` and `website`.

## Impact

- **Changed here:**
  - `tofu/repositories.tf`, `tofu/imports.tf`;
  - `oob/README.md`, `org-profile/CONTRIBUTING.md`;
  - `scripts/tests/test_guard_claude.py`;
  - two specs.
- **GitHub:**
  - the rename;
  - the ruleset update;
  - the labels recreated;
  - a sync commit into `.github`;
  - a PR in the website repository.
- **The site:** briefly served from the renamed repository's existing deployment, then redeployed. The bare
  `https://troupe-run.github.io/` stops serving the site; nothing links there.
- **The owner:**
  - approves the PR plan and the CI apply;
  - merges the website PR;
  - renames the local folder, if they'd rather do it themselves.
