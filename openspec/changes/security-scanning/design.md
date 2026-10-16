# Design: turn on Dependabot alerts, security updates and secret scanning in every repository

## Context

See proposal.md for why. What was found on 2026-10-16, before anything was written:

- **Live state.** All four managed repositories return 204 from `GET /repos/troupe-run/<repo>/vulnerability-alerts`,
  so Dependabot alerts are on in every one (#53 names only the website). In all four, `automated-security-fixes`
  reads `{"enabled": false}`. In `security_and_analysis`, `dependabot_security_updates`, `secret_scanning`,
  `secret_scanning_push_protection`, `secret_scanning_non_provider_patterns` and `secret_scanning_validity_checks`
  are all `disabled`. No repository has a `.github/dependabot.yml`, and none has an open Dependabot alert. The org is
  on the Free plan, and every `*_enabled_for_new_repositories` setting reads `false`.
- **Provider 6.13.0** (schema read in a scratch directory):
  - The `vulnerability_alerts` attribute on `github_repository` is deprecated: "Use the
    github_repository_vulnerability_alerts resource instead."
  - `github_repository_vulnerability_alerts` (`repository`, `enabled` defaulting to `true`) and
    `github_repository_dependabot_security_updates` (`repository`, `enabled` required) both import by repository
    name. Their source shows that **destroying either one turns its feature off**: Delete calls
    `DisableVulnerabilityAlerts` and `DisableAutomatedSecurityFixes`.
  - `security_and_analysis` accepts `secret_scanning` and `secret_scanning_push_protection`. It also accepts
    `advanced_security`, `code_security`, `secret_scanning_ai_detection` and `secret_scanning_non_provider_patterns`.
    `advanced_security` can't be set on a public repository.
- **The org's new-repository defaults.** GitHub's REST docs for "Update an organization" mark all six
  `*_enabled_for_new_repositories` parameters with "Endpoint closing down notice. Please use code security
  configurations instead." They still read back today. The provider has no resource for code security
  configurations. The org has only GitHub's built-in "GitHub recommended" configuration (id 17, `enforcement:
  unenforced`), and `GET .../code-security/configurations/defaults` returns `[]`, so no configuration applies to new
  repositories.
- **The App.** `troupe-run-infrastructure` has `administration: write` and `organization_administration: write`
  (`oob/app-installations.json`). That covers vulnerability alerts, automated security fixes, `security_and_analysis`
  and the org's settings.
- **The guard and Dependabot.** `run_ci` in `scripts/guard.py` applies the branch rule to every branch other than
  `main`, except a `release-please--` branch in `RELEASE_REPOSITORIES`. A Dependabot branch (`dependabot/...`) has no
  OpenSpec change, so `guard (workflow rules)`, which troupe and infrastructure both require, fails. The probe
  (D3) showed that Dependabot's commit is otherwise in shape: a Conventional Commit following the repository's
  history (`build(deps): Bump requests from 2.19.0 to 2.33.0`), signed off as `dependabot[bot] <support@github.com>`,
  which isn't the author's email (`49699333+dependabot[bot]@users.noreply.github.com`). Whether DCO accepts that is
  untested: the probe has no DCO check, and the branch rule refuses the pull request either way.
  `delivered_changes_by_others` would also refuse a Dependabot
  change to a delivered file in troupe (for example, an action version in `guard.yml`). The website requires only
  `test`, and has no guard or DCO.
- **The dependency graph is off** (found during the probe, 2026-10-16). `GET
  /repos/troupe-run/<repo>/dependency-graph/sbom` returns 404 for all four managed repositories and for the probe,
  while `cli/cli` returns 297 packages to the same login. A probe repository with `requests==2.19.0` and alerts and
  security updates on got no alert and no pull request in an hour. Alerts that read "on" can't fire without the
  graph. Nothing in the provider, in `security_and_analysis` or in the org's settings turns it on for an existing
  repository. The routes left are each repository's settings page, or a code security configuration.
- **Code security configurations** (REST docs, 2026-10-16). `POST /orgs/{org}/code-security/configurations` creates
  one; each feature is `enabled`, `disabled` or `not_set`, where `not_set` leaves a repository's own setting alone,
  and `enforcement` is `enforced` or `unenforced`. `POST .../{id}/attach` with `scope: selected` attaches it to
  listed repository IDs, and `PUT .../{id}/defaults` with `default_for_new_repos: public` makes it the default.
  `GET /repos/{owner}/{repo}/code-security-configuration` reads a repository's attachment, and returns 204 when
  there's none, as it does for the probe today. Writing needs `write:org`, which makes it the owner's action: the
  guard refuses org administration writes from agents.
- **Known provider behaviour**: any update to `github_repository` PATCHes the whole
  repository, and once turned a null homepage into `""`. An update to `security_and_analysis` is such an update, so it
  is proven on a throwaway repository first.

## Goals / Non-Goals

**Goals:**
- All five features (the dependency graph and the four #53 names) on in every managed repository, each declared, so
  turning one off shows in a plan or in `oob.py`.
- Dependabot alerts can actually fire: shown by a real alert and pull request on the probe.
- New repositories start with them on, and that is shown on a real new repository, not only read from the org's
  settings.
- Nothing the org's own automation commits is refused by push protection.
- A Dependabot pull request has a written, tested path, and none can merge into a governed repository through an
  exemption nobody chose.

**Non-Goals:**
- Dependabot version updates and `dependabot.yml` (#53 leaves them for later).
- Letting Dependabot pull requests merge in troupe or infrastructure: no branch exemption, no DCO handling, no commit
  prefix (owner, 2026-10-16).
- Code scanning, non-provider patterns, validity checks and AI detection. They weren't asked for, and some need
  Advanced Security on private repositories.
- Managing the configuration in OpenTofu: the provider has no resource for it (D4, D7).

## Decisions

### D1. Two resources in the repository module, not the deprecated attribute

The repository module gains `github_repository_vulnerability_alerts.this` and
`github_repository_dependabot_security_updates.this`, both `enabled = true`. Each depends on the repository through
`repository = github_repository.this.name`, and the security updates resource also `depends_on` the alerts resource,
since GitHub needs alerts on before it turns security updates on. Every module instance gets them, the probe
included, so the probe shows exactly what the live repositories get.

Both are imported for the four live repositories, with import blocks in `tofu/imports.tf`, following the file's
pattern. Alerts are already on, so the alerts import must plan no change: that is the adoption proof. The security
updates import plans one in-place change, `false` to `true`.

Alternatives:
- `vulnerability_alerts = true` on `github_repository`. It's deprecated and will be removed, and it would add another
  attribute to the whole-repository PATCH.
- Creating without import. It works, because the API calls are idempotent, but it skips the clean-plan proof the
  project requires before changing anything.

**Removing a repository from management** is already safe. The README's `removed { from = module.repo_<name> ...
destroy = false }` forgets the whole module, so it forgets both new resources too, and turns nothing off. The danger
is narrower: deleting either resource from the module, or setting `count` on it, destroys it, and that turns its
feature off in every repository. So both carry `prevent_destroy`, as the repository and the Pages site do: a plan
that would destroy one fails (owner, 2026-10-16). Deleting the resource block gets past `prevent_destroy`, so the
module's comment on the two resources says not to.

### D2. Secret scanning and push protection enabled in the module, for every repository

`security_and_analysis` sets `secret_scanning` and `secret_scanning_push_protection` to `enabled`. There's no
per-repository variable: every managed repository is public, and the spec makes these mandatory, so a variable would
only let one be turned off unseen. The other blocks stay undeclared, as they are today, and the plan has shown no
drift for them.

### D3. Prove it on a throwaway repository before any live plan

The probe (`tofu/probe/`) uses the same module, so after D1 and D2 it gets the same resources. On a new
`infra-probe-*` repository:

1. **No collateral change.** With the probe's other settings matching, apply with the features on, then read the
   repository back: the homepage, description, merge settings and topics are as they were.
2. **Push protection.** Commit the live encrypted `tofu/terraform.tfstate`, and deliver the guard with
   `probe_delivery = true`, which goes through the API as the live delivery does. Both must be accepted. As a
   positive control, so the result isn't meaningless, `git push` a file holding a fake token with a valid format and
   checksum. It must be refused. A probe that refuses nothing proves nothing.
3. **What Dependabot sends.** Attach the configuration (D4) to the probe only, and check that its dependency graph
   is on (the SBOM returns 200). Add a manifest that pins a dependency with a published advisory, then record the
   security-update pull request's branch name, commit message, author and whether it has a sign-off. That shape is
   what the guard test (D5) uses, and what `docs/development-workflow.md` describes.

The repository is deleted afterwards, along with the probe's local state, as the probe's header says.

### D4. A code security configuration turns the features on, and is the default for new repositories

The owner creates one configuration, "troupe-run baseline":

| Setting | Value |
|---|---|
| `dependency_graph`, `dependabot_alerts`, `dependabot_security_updates`, `secret_scanning`, `secret_scanning_push_protection` | `enabled` |
| `advanced_security` | `enabled` |
| every other feature (code scanning, the secret-scanning extras, private vulnerability reporting, delegated bypass and dismissal, autosubmit) | `not_set` |
| `code_security`, `secret_protection` | left out |
| `enforcement` | `unenforced` |

GitHub decided two of these rows when the configuration was created (2026-10-16). It refuses `code_security` and
`secret_protection`, even as `not_set`, on an org without the unbundled Advanced Security plan. And it needs
`advanced_security: enabled` whenever a feature it counts as Advanced Security, such as secret scanning, is
`enabled`. That costs nothing on public repositories, which always have it. GitHub's own "GitHub recommended"
configuration in the org sets it the same way. The configuration is attached only to public repositories and is the
default only for new public ones, so it never reaches a private repository, where it would be paid for.

It's attached to the four managed repositories (`scope: selected`), and set as the default for new public
repositories. `not_set` leaves everything #53 didn't ask for as each repository has it. `unenforced` can't lock the
owner out of a repository's settings, and it keeps OpenTofu's drift meaningful: a feature turned off by hand still
shows in the plan, rather than being impossible to turn off.

The order is: the probe first (D3, step 3), then the four live repositories and the default, before the pull request.
So the pull request's plan and `oob.py` output are evidence of the end state, and a new `infra-probe-*` repository,
created by the owner after the default is set, shows the org-settings scenario before merge. It's deleted afterwards.

**`org.tf` no longer decides anything here.** Its five `*_enabled_for_new_repositories` attributes are set to
whatever `GET /orgs/troupe-run` reads once the configuration is the default, so the plan stays clean. Their comment
says the configuration in `oob/` is what decides, and that GitHub has marked the parameters as closing down.
`advanced_security_enabled_for_new_repositories` stays `false`.

Alternatives:
- **The `org.tf` parameters, as first designed.** They're closing down, and they can't turn the graph on in an
  existing repository, which is the gap that matters.
- **Turning the graph on in each repository's settings by hand, with `oob.py` checking it.** That leaves new
  repositories relying on the closing-down parameters, and adds one hand step per new repository. The owner chose the
  configuration (2026-10-16).

### D7. `oob.py` checks the configuration, its attachments, the default and each dependency graph

`oob/code-security.json` declares the configuration by name, with every setting from D4, the default
(`default_for_new_repos: public`), and the repositories it's attached to: the four managed ones. `scripts/oob.py`
reads `GET /orgs/troupe-run/code-security/configurations`, `.../defaults` and each managed repository's
`code-security-configuration`, and reports any difference, as its other checks do. A configuration on GitHub that
isn't declared is reported too.

It also reads each managed repository's `dependency-graph/sbom`. A 200 means the graph is on, and a 404 means it's
off, which is reported. Any other status, or a response it can't read, is an error that names the repository and
the status. It's never treated as "off", or as "on" (the malformed-input rule). Each check has a test that fails when
it breaks, in `scripts/tests/test_oob.py`. `oob/README.md` gains the row for it.

### D5. A Dependabot pull request is an alert that comes with a fix

In troupe and infrastructure, a Dependabot pull request isn't merged. Whoever picks it up opens an issue (or uses the
alert's) and an OpenSpec change that applies the same bump on a branch named after the change. That pull request
closes the issue. Dependabot's pull request is closed with a comment linking the change. Dependabot closes its own
pull request once the vulnerable version is gone from the default branch anyway. On the website, a Dependabot pull
request merges once `test` passes, like any other pull request there.

The guard doesn't change. A test in `scripts/tests/test_guard_push_and_ci.py` checks that `run_ci` refuses a branch
named like D3's observed Dependabot branch, in `troupe-run/troupe` and in `troupe-run/infrastructure`, on the
branch-change rule. It pins the decision, so a later exemption has to be a deliberate change to this test and its
scenario. `docs/development-workflow.md` gains a short "Dependabot pull requests" section, and a Known gaps entry: a
security fix waits for a person, it doesn't merge itself.

Alternative: an exemption like release-please's, with a ruleset that reserves `dependabot/*` for Dependabot, DCO
handling and a commit prefix. The owner chose not to do it now (2026-10-16). It becomes a follow-up issue if these
pull requests turn out to be frequent.

### D6. Secret scanning's first scan is triaged in this change

Turning secret scanning on scans each repository's full history. Once the configuration is attached to the four
repositories (D4), before the pull request, the open alerts in all four repositories are listed (`GET
/repos/troupe-run/<repo>/secret-scanning/alerts`). Each one is triaged in the pull request's evidence: what it is,
and whether it's a real secret that needs rotating (the owner's job) or a false positive the owner dismisses. Alert contents are never pasted: the location and type only.

## Risks / Trade-offs

- [Push protection refuses a CI state commit after an apply, leaving the applied change uncommitted] → D3 commits the
  real encrypted state to a protected throwaway repository. The state's ciphertext is base64 in JSON, and GitHub's
  provider patterns are prefixed, checksummed formats, so a match by chance is very unlikely. If it ever happens, the
  run fails and keeps the state as its `state-after-apply` artifact, and the README's recovery for that case applies.
- [Attaching the configuration turns the features on outside a plan] → it's the owner's own write, made for this
  change. The next plan shows what OpenTofu still needs to adopt, and the pull request carries that plan.
- [The configuration and OpenTofu disagree later] → each declares the same five features. A difference in what
  OpenTofu manages shows in the daily plan. A difference in the configuration, its attachments, its default or a
  dependency graph shows only when someone runs `oob.py`, with every plan as `oob/README.md` says: nothing checks
  those daily yet. If the graph is turned off by hand, Dependabot goes quiet until the next run. Running `oob.py`
  daily in CI is #62 (owner, 2026-10-16).
- [Deleting one of the new resources from the module turns its feature off everywhere] → D1: `prevent_destroy`
  fails a plan that would destroy one. Deleting the block itself gets past that, so the module's comment says not
  to, and the plan would show four destroys for the owner to refuse.
- [The live PATCH changes a setting nobody meant to change] → D3's first probe, then the live plan must show only the
  intended diffs before the owner approves it.
- [A Dependabot pull request sits open and red in troupe or infrastructure] → D5 says what to do with it, and alerts
  are emailed to the owner as before. It's the cost of no exemption, and the owner chose it.
- [GitHub removes the closing-down parameters entirely] → the provider would then error or show drift on `org.tf`.
  Nothing depends on them any more (D4), so the fix is deleting the five attributes.
