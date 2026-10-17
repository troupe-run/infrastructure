# Outside OpenTofu's control

These parts of the org can't be managed by OpenTofu, so this directory declares them and
`scripts/oob.py` checks GitHub against the declarations. It only reads: it prints every
difference and exits 1 if there are any. Fix the difference on GitHub, or change the
declaration here in a pull request (design D6 in `openspec/changes/archive/2026-10-11-adopt-org/`).

Checked against provider `integrations/github` 6.13.0 with `tofu providers schema` (2026-10-11).

| File | What it declares | Why OpenTofu can't manage it | Read with |
|---|---|---|---|
| `issue-types.json` | the org's issue types: name, description, colour, enabled | the provider has no resource or data source for issue types | `gh api orgs/troupe-run/issue-types` |
| org-profile/ (derived) | the files `troupe-run/.github` should hold: exactly the files under `org-profile/` | `github_repository_file` manages declared files only, so a file added by hand would never show in a plan | `gh api repos/troupe-run/.github/git/trees/main` |
| `app-installations.json` | each App installed in the org: its permissions and repository selection | the provider can't read installations as the App (403, design D9) | `gh api orgs/troupe-run/installations` |
| `org-settings.json` | org settings the provider has no attribute for: today, whether 2FA is required | `github_organization_settings` has no two-factor attribute | `gh api orgs/troupe-run` |
| `projects.json` | the org's projects: number, title, public, closed, short description, and the repositories each is linked to. The owner links one with `gh project link <n> --owner troupe-run --repo troupe-run/<repo>`; the guard leaves that to the owner. A linked repository needs `has_projects = true` in `tofu/repositories.tf`, or the project is hidden there (spec: repositories) | the provider supports only classic Projects; ours are Projects v2, and it can't link one to a repository | `gh api graphql` (`projectsV2`, with `repositories`) |
| `code-security.json` | the "troupe-run baseline" code security configuration: its settings, that it's the default for new public repositories, and the managed repositories it's attached to, each with its dependency graph on. A configuration added on GitHub is reported too. A dependency graph that can't be read is an error, never "off" (security-scanning design D7) | the provider has no resource for code security configurations, and nothing it can set turns a repository's dependency graph on, which Dependabot alerts need | `gh api orgs/troupe-run/code-security/configurations` (and `.../defaults`), `gh api repos/troupe-run/<repo>/code-security-configuration`, `gh api repos/troupe-run/<repo>/dependency-graph/sbom` (404: off) |
| `tofu/labels/troupe.json` (derived) | a `cap:<name>` label for each folder in troupe's `openspec/specs/`. One way: a label with no spec isn't reported, since a label can come before its spec. The fix is a pull request adding the label (spec: labels) | OpenTofu manages the labels but can't read troupe's files | `gh api repos/troupe-run/troupe/contents/openspec/specs` |
| `tofu/milestones.json` (derived) | the release milestones on each listed repository: any milestone, open or closed, whose title isn't declared is reported. One way: a declared milestone that's missing or different shows in the plan, since OpenTofu manages it (spec: milestones) | `github_repository_milestone` manages declared milestones only, so one made by hand would never show in a plan | `gh api "repos/troupe-run/<repo>/milestones?state=all"` |
| `troupe-spec-purposes.json` | for each `cap:<name>` label whose troupe spec exists, the spec's Purpose its description was written from, verbatim. A Purpose that has changed, a labelled spec with nothing recorded, and a record with no spec are each reported (spec: labels) | OpenTofu manages the descriptions but can't read troupe's specs to tell when one is out of date | `gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md` |

**A new capability's label** gets a description of 100 characters or fewer that says what the capability covers
(`scripts/tests/test_labels.py` refuses one that only repeats the name). If troupe has a spec for it, shorten the
spec's Purpose and record that Purpose here, with its whitespace collapsed, in the same pull request. If nothing in
troupe defines it yet, the description is `TBD`. When `oob.py` reports a changed Purpose, review the description
against the new text and update both files together.

Run it with your own `gh` login, which needs read access to the org:

```
uv run scripts/oob.py
```

It isn't run by CI: CI holds no credentials yet. Run it alongside every plan, and quote its
output in the pull request.

## Which repositories each App is installed on (confirmed by hand)

No token this repo can hold is allowed to read these lists: the App's own installation token, `gh`'s OAuth token and
a classic personal access token (even with `repo`) were all refused with a 403 on 2026-10-11 (design D9). So the
lists below are checked by hand in each App's settings, by any change that adds, removes or depends on a repository
(spec: teams-and-access).

| App | Repositories | Confirmed |
|---|---|---|
| `troupe-run-infrastructure` | `troupe`, `.github`, `infrastructure`, `website` | 2026-10-11, owner |
| `dco` | `troupe`, `.github`, `infrastructure` | 2026-10-11, owner |
| `troupe-run-release` | `troupe` | 2026-10-13, owner |

A repository the infrastructure App isn't installed on shows only its public view to OpenTofu (merge settings read as
off, no security settings), so the first plan after adding one will show that it's missing from this list.

## troupe's release App (set up by hand)

troupe's release workflow (troupe-run/troupe#23) opens release pull requests with the `troupe-run-release` App's
token, because a pull request opened with `GITHUB_TOKEN` starts no workflows (spec: release-credentials). GitHub has no
API for creating an App, and OpenTofu never holds a secret, so these steps are the owner's. The App's ID, client ID and
bot user ID are recorded on #34. `tofu/release.tf` declares the `release` environment and the client-ID variable.

**Creating it** (done 2026-10-13). In the org's settings, under GitHub Apps, create a new App:
- name `troupe-run-release`, installable only on this account, webhook off;
- repository permissions: contents, issues and pull requests read and write, metadata read. No organisation or
  account permissions;
- install it on `troupe` only, and add its row to the table above.

Its installation is checked by `oob.py` against `app-installations.json`. Its client ID goes in `tofu/release.tf`.

**Its key.** Generate a private key in the App's settings. Store it in 1Password as an SSH Key item named
`troupe-run-release` in vault `troupe.run`, by importing the downloaded `.pem`, then delete the file. Once the
`release` environment exists (after the apply that creates it), set the secret. Nothing is printed:

```sh
export OP_ACCOUNT=l-a-u.1password.com
op read -n "op://troupe.run/troupe-run-release/private key" \
  | gh secret set RELEASE_APP_PRIVATE_KEY --env release -R troupe-run/troupe
```

Check it by name, never by value:

```sh
gh api repos/troupe-run/troupe/environments/release/secrets --jq '.secrets[].name'
```

**Rotating the key.** Generate a new key in the App's settings, replace the 1Password item's key with it, and run the
command above again. Then delete the old key in the App's settings. A release run between the two steps still works,
because both keys are valid until the old one is deleted.

**The infrastructure App's "Variables: write"** was granted for this (2026-10-13), so OpenTofu can write
`RELEASE_APP_CLIENT_ID`. It's declared in `app-installations.json`.

## troupe.run's DNS (set up by hand)

troupe.run is registered at Gandi and served by Cloudflare. `tofu/dns.tf` manages its records (spec: dns). The zone,
the token and the nameservers are set up by hand, because managing them would need an account-wide token, or Gandi's
dormant provider (manage-dns-as-code design D1, D2). Done 2026-10-17.

**The account.** Cloudflare account `troupe.run` (`32b1f418aad2938f5d7dc5a8ad51226c`), on the free plan, holds only
troupe-run's zones. hps.gd's zones go in a separate account, so no token or member made for them can reach troupe.run.
Two-factor login is required on it, and on the Gandi account that holds the registration: either login can repoint
troupe.run without a plan.

**The zone.** `troupe.run` (`f716f063a26f15bcfcecd62791cdd202`). Cloudflare's scan copied Gandi's ten records when it
was added, and the owner added the Pages verification record; all eleven were imported, not recreated. Its settings
are Cloudflare's defaults: nothing is proxied, so they don't touch the site. If a CAA answer at the apex ever shows CAs
that `dns.json` doesn't declare, Cloudflare is adding its own for Universal SSL: turn that off for the zone.

**The token.** A custom account API token with Zone → DNS → Edit and Zone → Zone → Read, on troupe.run only, no IP
filter and no expiry. It's in 1Password as `troupe-run-cloudflare-dns`, field `credential`, in vault `troupe.run`, and
in CI's three environments as `TF_VAR_cloudflare_api_token` (README). Check its scope without printing it:

```sh
export OP_ACCOUNT=l-a-u.1password.com
op run --env-file=tofu/secrets.env -- sh -c 'curl -s -H "Authorization: Bearer $TF_VAR_cloudflare_api_token" \
  https://api.cloudflare.com/client/v4/zones | python3 -c "import json,sys; print([z[\"name\"] for z in json.load(sys.stdin)[\"result\"]])"'
```

It should list `troupe.run` and nothing else. To rotate it, create the new token with the same permissions, replace the
1Password item's credential, run the README's environment-secret loop, then delete the old token in Cloudflare.

**The nameservers.** At Gandi, troupe.run's nameservers are `audrey.ns.cloudflare.com` and
`sterling.ns.cloudflare.com`. A plan warns when Cloudflare doesn't report the zone active, which is what changing them
causes. **Rollback:** set Gandi's three back (`ns-25-c.gandi.net`, `ns-61-b.gandi.net`, `ns-150-a.gandi.net`). Gandi's
LiveDNS zone still holds the original records, without the mail lockdown, the CAA policy or the Pages verification
record, so add those there first if the rollback is to keep them. No DS record is published, so there's no DNSSEC to
undo (#72).
