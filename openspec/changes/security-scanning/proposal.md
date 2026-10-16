# Proposal: turn on Dependabot alerts, security updates and secret scanning in every repository

## Why

The repository module hard-codes secret scanning and push protection to `disabled`, and `org.tf` turns every security
feature off for new repositories. Dependabot alerts are on in all four managed repositories (`GET
/repos/troupe-run/<repo>/vulnerability-alerts` returned 204 for each on 2026-10-16, not only the website as #53
says), but nothing declares them, so turning them off wouldn't show in a plan. The owner asked for all four features
to be on (#53, 2026-10-16). Every repository is public, so they're free.

Alerts that read "on" don't fire yet. The dependency graph is off in all four repositories: their
`dependency-graph/sbom` returns 404, while a public repository with a graph returns its packages to the same login. So
Dependabot sees no dependencies, and a probe repository with a vulnerable pin got no alert in an hour. No provider
attribute, `security_and_analysis` field or org setting turns the graph on for an existing repository.

## What Changes

- Every managed repository (`troupe`, `.github`, `infrastructure`, `website`) has these on, declared in the repository
  module:
  - Dependabot alerts, as a `github_repository_vulnerability_alerts` resource. This is imported, since alerts are
    already on. The provider has deprecated the `vulnerability_alerts` attribute on `github_repository`.
  - Dependabot security updates, as a `github_repository_dependabot_security_updates` resource. This is imported, then
    turned on.
  - Secret scanning and push protection, set to `enabled` in `security_and_analysis`.
- A code security configuration, "troupe-run baseline", turns on the dependency graph, Dependabot alerts, security
  updates, secret scanning and push protection, and leaves everything else `not_set` (owner, 2026-10-16). The owner
  creates it, attaches it to the four managed repositories, and makes it the default for new public repositories.
  The provider can't manage configurations, so it's declared in `oob/`. `scripts/oob.py` checks its settings, each
  managed repository's attachment, the default, and each managed repository's dependency graph.
- `org.tf`'s five `*_enabled_for_new_repositories` attributes no longer decide anything: GitHub has marked them as
  closing down. They're set to whatever GitHub reads once the configuration is the default, with a comment pointing
  to `oob/`. Advanced Security stays `false`.
- A Dependabot pull request in a governed repository (`troupe`, `infrastructure`) is treated as an alert that comes
  with a fix (owner, 2026-10-16). It can't merge as it is, because the guard's branch rule and DCO refuse it. Its fix
  goes through an issue and an OpenSpec change like any other change, and the Dependabot pull request is closed with
  a link to that change. `docs/development-workflow.md` says so. The guard doesn't change. A test pins the refusal,
  so an exemption can't arrive by accident.
- Probes on a throwaway repository show:
  - turning the features on PATCHes nothing else on the repository;
  - push protection accepts the encrypted state and the guard's delivered files, and refuses a token-shaped string;
  - what a Dependabot security update pull request looks like (branch, commit message, author, sign-off).

Out of scope:
- Dependabot *version* updates (`dependabot.yml`), which are a file in each repository, not a setting (#53).
- An exemption that lets Dependabot pull requests merge in governed repositories. That becomes a follow-up issue if
  they turn out to be frequent.
- Code scanning, and the secret-scanning extras: non-provider patterns, validity checks and AI detection. The
  configuration leaves them `not_set`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repositories`: a new requirement that every managed repository has the dependency graph, Dependabot alerts,
  Dependabot security updates, secret scanning and push protection on and declared, so turning any of them off shows
  as drift.
- `org-settings`: a new requirement that the org's defaults turn these features on for new repositories.
- `development-workflow`: "The rules are re-checked on GitHub" gains a scenario. A Dependabot pull request in a
  governed repository fails the branch rule, because there's no exemption for it.

## Impact

- `tofu/modules/repository/main.tf`: `security_and_analysis` enabled, plus two new resources per repository. The
  imports go in `tofu/imports.tf`.
- `tofu/org.tf`: the five `*_enabled_for_new_repositories` attributes match what GitHub reads after the
  configuration is the default, and their comment points to `oob/`.
- `oob/code-security.json`, a new check in `scripts/oob.py` with its tests, and a row in `oob/README.md`.
- The owner's four writes to the org, with `gh api`: create the configuration, attach it to the probe, attach it to
  the four repositories, and set it as the default. Attaching it turns the features on before the apply.
- Once the configuration is attached, the apply adopts what it turned on. Secret scanning then scans each
  repository's full history, and any alert it raises is triaged in this change.
- From then on, pushes and API commits in all four repositories are checked for secrets. That includes the App's
  state commits and guard deliveries.
- `docs/development-workflow.md`: how a Dependabot pull request is handled.
- `scripts/tests/`: a test that a `dependabot/` branch fails the branch rule on GitHub.
- No repository has an open Dependabot alert today, so turning security updates on opens no pull requests straight
  away.
