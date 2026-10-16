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
  OpenSpec change, so `guard (workflow rules)`, which troupe and infrastructure both require, fails. Dependabot's
  commits carry no `Signed-off-by`, so `DCO` fails too. `delivered_changes_by_others` would also refuse a Dependabot
  change to a delivered file in troupe (for example, an action version in `guard.yml`). The website requires only
  `test`, and has no guard or DCO.
- **Known provider behaviour**: any update to `github_repository` PATCHes the whole
  repository, and once turned a null homepage into `""`. An update to `security_and_analysis` is such an update, so it
  is proven on a throwaway repository first.

## Goals / Non-Goals

**Goals:**
- All four features on in every managed repository, each declared, so turning one off shows in a plan.
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
- Moving the org's defaults to a code security configuration while the declared settings still work (D4).

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
feature off in every repository. The module's comment on the two resources says so.

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
3. **What Dependabot sends.** Add a manifest that pins a dependency with a published advisory, then record the
   security-update pull request's branch name, commit message, author and whether it has a sign-off. That shape is
   what the guard test (D5) uses, and what `docs/development-workflow.md` describes.

The repository is deleted afterwards, along with the probe's local state, as the probe's header says.

### D4. The org's defaults stay declared in `org.tf`, and are proven on a new repository

`org.tf` sets these to `true`: `dependabot_alerts_enabled_for_new_repositories`,
`dependabot_security_updates_enabled_for_new_repositories`, `dependency_graph_enabled_for_new_repositories`,
`secret_scanning_enabled_for_new_repositories` and `secret_scanning_push_protection_enabled_for_new_repositories`.
The dependency graph is always on for public repositories, but Dependabot alerts need it, and members can create
private ones. `advanced_security_enabled_for_new_repositories` stays `false`: it's always on for public repositories,
and it's paid for private ones.

These parameters are closing down, so reading them back isn't enough. GitHub could accept the PATCH, return `true`
and still apply nothing to a new repository. After the apply, the owner creates a new `infra-probe-*` repository
(creating a repository is the owner's action), and its security settings are read. All four must be on with nothing
applied to it. Then it's deleted.

**Fallback, if the probe shows them off:** a custom code security configuration with exactly these features, set as
the default for new public repositories. The provider can't manage it, so it's declared in `oob/` and checked by
`scripts/oob.py`, as issue types are. The owner creates it, since it's an org administration write. The five
`org.tf` attributes then go back to whatever GitHub reads, so the plan stays clean, with a comment pointing to the
`oob/` declaration. This is decided now, so the apply step doesn't stall on a new design question.

Alternative: go straight to a code security configuration. It moves a setting OpenTofu can declare today out of
OpenTofu, before GitHub has stopped honouring it, and the issue asks for the defaults in `org.tf`.

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

Turning secret scanning on scans each repository's full history. After the apply, the open alerts in all four
repositories are listed (`GET /repos/troupe-run/<repo>/secret-scanning/alerts`). Each one is triaged in the pull
request's evidence: what it is, and whether it's a real secret that needs rotating (the owner's job) or a false
positive the owner dismisses. Alert contents are never pasted: the location and type only.

## Risks / Trade-offs

- [Push protection refuses a CI state commit after an apply, leaving the applied change uncommitted] → D3 commits the
  real encrypted state to a protected throwaway repository. The state's ciphertext is base64 in JSON, and GitHub's
  provider patterns are prefixed, checksummed formats, so a match by chance is very unlikely. If it ever happens, the
  run fails and keeps the state as its `state-after-apply` artifact, and the README's recovery for that case applies.
- [The org's defaults are accepted and ignored] → D4 checks them on a real new repository, with a fallback already
  decided.
- [Deleting one of the new resources from the module turns its feature off everywhere] → D1: the module's comment
  says so, and the plan would show four destroys of that resource for the owner to refuse.
- [The live PATCH changes a setting nobody meant to change] → D3's first probe, then the live plan must show only the
  intended diffs before the owner approves it.
- [A Dependabot pull request sits open and red in troupe or infrastructure] → D5 says what to do with it, and alerts
  are emailed to the owner as before. It's the cost of no exemption, and the owner chose it.
- [GitHub removes the closing-down parameters entirely] → the provider would then error or show drift on `org.tf`.
  D4's fallback is the fix, and the daily plan shows it within a day.
