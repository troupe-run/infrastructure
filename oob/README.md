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
| `tofu/labels/troupe.json` (derived) | the capability labels each spec in troupe's `openspec/specs/` names in its `Capability:` line, the first non-blank line of its Purpose: ``Capability: `cap:<name>`, `cap:<name>` ``, one or more labels in backticks, nothing after the last. A spec that names no label, a line in any other shape, and a label that isn't declared are each reported. One way: a label no spec names isn't reported, since a label can come before its spec. The fix is a pull request adding the label, or a fix to the spec in troupe (spec: labels) | OpenTofu manages the labels but can't read troupe's files | `gh api repos/troupe-run/troupe/contents/openspec/specs`, then each `<name>/spec.md` |
| `tofu/milestones.json` (derived) | the release milestones on each listed repository: any milestone, open or closed, whose title isn't declared is reported. One way: a declared milestone that's missing or different shows in the plan, since OpenTofu manages it (spec: milestones) | `github_repository_milestone` manages declared milestones only, so one made by hand would never show in a plan | `gh api "repos/troupe-run/<repo>/milestones?state=all"` |
| `tofu/labels/troupe.json` (derived) | the troupe roadmap board's `Capability` field: a single select whose options are exactly the declared `cap:*` names without the prefix, each with its label's description. Both ways: a label with no option, and an option with no label, are each reported, and so is an option whose description isn't its label's. The owner adds and removes options in the field's settings on GitHub. Their descriptions are set by `scripts/board_options.py` in the `tofu` workflow: the plan of `main` lists them for approval, and the `board` job sets them after the apply, sending every option back with its id (spec: labels) | the provider supports only classic Projects, and changing a field's options is owner-only in the guard | `gh api graphql` (`projectV2(number: 1)`, `field(name: "Capability")`, each option's `name` and `description`) |
| `troupe-spec-purposes.json` | for each troupe spec, by its folder name, its Purpose without the `Capability:` line, verbatim. The descriptions of the labels it names were written from it. A Purpose that has changed, a spec with nothing recorded, and a record with no spec are each reported, naming the spec's labels. A change to the `Capability:` line alone isn't (spec: labels) | OpenTofu manages the descriptions but can't read troupe's specs to tell when one is out of date | the same `spec.md` reads as the row above |

**A new capability's label** is added by the steps in
[docs/standard-changes.md](../docs/standard-changes.md#a-capability-label), as a standard change. It gets a
description of 100 characters or fewer that says what the capability covers
(`scripts/tests/test_labels.py` refuses one that only repeats the name). A label's description covers every troupe
spec that names it, so write it from those specs' Purposes. If nothing in troupe defines it yet, the description is
`TBD`. **A new troupe spec** gets its Purpose recorded here by its folder name, without the `Capability:` line and with
its whitespace collapsed. When `oob.py` reports a changed Purpose, review the descriptions of the labels it names
against the new text, and update the descriptions and the record together.

Run it with your own `gh` login, which needs read access to the org:

```
uv run scripts/oob.py
```

Run it alongside every plan of a pull request, and quote its output in the pull request: CI doesn't run it on pull
requests.

**The infrastructure App's "Issue types: read" and "Projects: read"** (organisation permissions, granted by the
owner on 2026-10-18) are what let CI read the org's issue types and projects. Nothing else uses them. They're
declared in `app-installations.json`.

**CI runs it too,** in `tofu.yml`'s `drift (out of band)` job, whenever `main` is planned: daily at 06:00 UTC, after
CI passes on a merge, and on `gh workflow run tofu.yml --ref main`. The job runs `uv run scripts/oob.py --ci` in the
`plan-main` environment, with an installation token of the infrastructure App that can only read (spec: ci-apply).
It runs every check a hand run does, App installations included. A difference, or a check it couldn't read, fails
the job, and the run's summary lists each one with the checks it ran. Which repositories each App is installed on is
still unreadable to any token, so the table below stays confirmed by hand.

**How a failure reaches you.** GitHub emails a failed scheduled run to whoever last changed the workflow's `cron`
line, and a failed run after a merge to whoever's push started it, but only if their notification settings send
failed Actions runs (Settings → Notifications → Actions). The `cron` line was last changed by the owner. A change to
it moves the emails to whoever makes that change, so keep it the owner's, or check the setting again
(run-oob-check-daily design D5).

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
| `troupe-run-board` | none | 2026-10-18, by the App's own token (`GET /installation/repositories` returned `[]`) |
| `troupe-run-docs` | `website` | 2026-10-19, by the App's own token (`GET /installation/repositories` returned `website` only) |
| `troupe-run-dependabot` | `troupe`, `infrastructure`, `website` | 2026-10-27, by the App's own token (`GET /installation/repositories`, after the probe repository was deleted) |
| `troupe-run-review` | `troupe`, `infrastructure`, `website` | 2026-10-26, owner |

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
# gh runs only once op has read the key, so a failed read can't set an empty secret.
key=$(op read -n "op://troupe.run/troupe-run-release/private key") &&
  printf '%s' "$key" | gh secret set RELEASE_APP_PRIVATE_KEY --env release -R troupe-run/troupe
unset key
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

## The board App (set up by hand)

website's weekly link check opens its "Broken external links" issue, and this repository's schedule watch its
"Scheduled workflows stopped running" issue, with `GITHUB_TOKEN`, which can't write to an org project. In each, a job
of its own adds the issue to the troupe roadmap board with the `troupe-run-board` App's token instead (spec:
board-credentials, #59, #60). GitHub has no API for creating an App, and OpenTofu never holds a secret, so these steps
are the owner's. The App's IDs are recorded on #59. `tofu/board.tf` declares a `board` environment and the client-ID
variable on website and on infrastructure.

**Creating it** (done 2026-10-18). In the org's settings, under GitHub Apps, create a new App:
- name `troupe-run-board`, installable only on this account, webhook off;
- organisation permission "Projects: read and write", and nothing else: no repository or account permissions;
- install it with "Only select repositories" and select none. It reads the public issues it adds without being
  installed on their repository, so the table above lists none (add-link-issue-to-board design D6). If website goes
  private, adding its issues fails, and the App would need website and "Issues: read".

Its installation is checked by `oob.py` against `app-installations.json`. Its client ID goes in `tofu/board.tf`.

**Its key.** Generate a private key in the App's settings. Store it in 1Password as an SSH Key item named
`troupe-run-board` in vault `troupe.run`, by importing the downloaded `.pem`, then delete the file. Once the `board`
environment exists in a repository (after the apply that creates it), set the secret there. Nothing is printed:

```sh
export OP_ACCOUNT=l-a-u.1password.com
# gh runs only once op has read the key, so a failed read can't set an empty secret.
key=$(op read -n "op://troupe.run/troupe-run-board/private key") &&
  printf '%s' "$key" | gh secret set BOARD_APP_PRIVATE_KEY --env board -R troupe-run/website &&
  printf '%s' "$key" | gh secret set BOARD_APP_PRIVATE_KEY --env board -R troupe-run/infrastructure
unset key
```

Check each by name, never by value:

```sh
gh api repos/troupe-run/website/environments/board/secrets --jq '.secrets[].name'
gh api repos/troupe-run/infrastructure/environments/board/secrets --jq '.secrets[].name'
```

**Rotating the key.** Generate a new key in the App's settings, replace the 1Password item's key with it, and run both
commands above again. Then delete the old key in the App's settings. A run between the two steps still works, because
both keys are valid until the old one is deleted.

## The docs App (set up by hand)

troupe's workflows start the website's docs build on every push to troupe's `main` and every new `troupe-v*` tag
(troupe-run/troupe#120). A run's `GITHUB_TOKEN` covers only its own repository, so the job that sends the trigger
mints the `troupe-run-docs` App's token, which can start a `workflow_dispatch` run on website and write nothing there
(spec: docs-build-credentials, #109). GitHub has no API for creating an App, and OpenTofu never holds a secret, so
these steps are the owner's. The App's IDs are recorded on #109. `tofu/docs.tf` declares a `docs` environment and the
client-ID variable on troupe. The sending step and the website's side are troupe-run/website#23's.

The same App's token also rebuilds the site when `tofu/milestones.json` changes on infrastructure's `main`
(`.github/workflows/milestones-notice.yml`, spec: milestones, #124). So `tofu/docs.tf` declares the same environment
and variable on infrastructure, and the key is set there too (rebuild-site-on-milestones design D1).

**Creating it** (done 2026-10-19). In the org's settings, under GitHub Apps, create a new App:
- name `troupe-run-docs`, installable only on this account, webhook off;
- repository permission "Actions: read and write", and nothing else: no organisation or account permissions. GitHub
  adds "Metadata: read";
- install it with "Only select repositories" and select `website` only. It needn't be installed on troupe: the run
  mints a token for website's installation.

Its installation is checked by `oob.py` against `app-installations.json`. Its client ID goes in `tofu/docs.tf`.

**Its key.** Generate a private key in the App's settings. Store it in 1Password as an SSH Key item named
`troupe-run-docs` in vault `troupe.run`, by importing the downloaded `.pem`, then delete the file. Once the `docs`
environment exists on troupe and on infrastructure (after the apply that creates each), set the secret in both.
Nothing is printed:

```sh
export OP_ACCOUNT=l-a-u.1password.com
# gh runs only once op has read the key, so a failed read can't set an empty secret.
key=$(op read -n "op://troupe.run/troupe-run-docs/private key") &&
  printf '%s' "$key" | gh secret set DOCS_APP_PRIVATE_KEY --env docs -R troupe-run/troupe &&
  printf '%s' "$key" | gh secret set DOCS_APP_PRIVATE_KEY --env docs -R troupe-run/infrastructure
unset key
```

Check each by name, never by value:

```sh
gh api repos/troupe-run/troupe/environments/docs/secrets --jq '.secrets[].name'
gh api repos/troupe-run/infrastructure/environments/docs/secrets --jq '.secrets[].name'
```

**Rotating the key.** Generate a new key in the App's settings, replace the 1Password item's key with it, and run both
commands above again. Then delete the old key in the App's settings. A run between the two steps still works, because
both keys are valid until the old one is deleted.

## The Dependabot issues App (set up by hand)

`.github/workflows/dependabot-issues.yml` gives every Dependabot pull request in troupe, website and infrastructure its
issue, and adds `Closes #<n>` to the pull request's description (spec: dependency-updates, dependabot-issue-credentials,
#172). `GITHUB_TOKEN` can't write the other repositories, and its edits start no workflow, so the closing line wouldn't
re-run `guard`. So the run writes with the `troupe-run-dependabot` App's token, which can write issues and pull
requests' descriptions, and can't push or merge (probed 2026-10-27: both refused with 403). GitHub has no API for
creating an App, and OpenTofu never holds a secret, so these steps are the owner's. The App's IDs are recorded on
#172. `tofu/dependabot_issues.tf` declares a `dependabot-issues` environment and the client-ID variable on
infrastructure. The board card is added with the board App's token, in the `board` environment.

**Creating it** (done 2026-10-27). In the org's settings, under GitHub Apps, create a new App:
- name `troupe-run-dependabot`, installable only on this account, webhook off. The script trusts only issues by
  `troupe-run-dependabot[bot]`, so a different name means changing `APP` in `scripts/dependabot_issues.py` too;
- repository permissions "Issues: read and write" and "Pull requests: read and write", and nothing else: no
  organisation or account permissions. GitHub adds "Metadata: read". Setting an issue's type needs nothing more;
- install it with "Only select repositories" and select `troupe`, `infrastructure` and `website`. The run's token
  names no repositories, so it covers exactly these.

Its installation is checked by `oob.py` against `app-installations.json`. Its client ID goes in
`tofu/dependabot_issues.tf`.

**Its key.** Generate a private key in the App's settings. Store it in 1Password as an SSH Key item named
`troupe-run-dependabot` in vault `troupe.run`, by importing the downloaded `.pem`, then delete the file. Once the
`dependabot-issues` environment exists on infrastructure (after the apply that creates it), set the secret. Nothing
is printed:

```sh
export OP_ACCOUNT=l-a-u.1password.com
# gh runs only once op has read the key, and only if it's PKCS#1 or PKCS#8 (create-github-app-token refuses OpenSSH).
key=$(op read -n "op://troupe.run/troupe-run-dependabot/private key") &&
  case "$key" in "-----BEGIN RSA PRIVATE KEY-----"*|"-----BEGIN PRIVATE KEY-----"*) ;; *) false ;; esac &&
  printf '%s' "$key" | gh secret set DEPENDABOT_APP_PRIVATE_KEY --env dependabot-issues -R troupe-run/infrastructure
unset key
```

Check it by name, never by value:

```sh
gh api repos/troupe-run/infrastructure/environments/dependabot-issues/secrets --jq '.secrets[].name'
```

**Rotating the key.** Generate a new key in the App's settings, replace the 1Password item's key with it, and run the
command above again. Then delete the old key in the App's settings. A run between the two steps still works, because
both keys are valid until the old one is deleted.

## The review App and the Claude token (set up by hand)

`.github/workflows/claude-review.yml` reviews each member's pull request in troupe, infrastructure and website with
Claude (spec: pr-review, #154). It needs two credentials, and OpenTofu never holds a secret, so these steps are the
owner's. Its comments come from `troupe-run-review[bot]`: the run writes only with a token for the `troupe-run-review`
App, which can read code and write on pull requests and nothing else. It doesn't use Anthropic's Claude GitHub App,
whose token can write contents whatever the workflow asks for (claude-pr-review design D1).

**Creating the App** (done 2026-10-26). In the org's settings, under GitHub Apps, create a new App:
- name `troupe-run-review`, installable only on this account, webhook off;
- repository permissions "Contents: read" and "Pull requests: read and write", and nothing else; GitHub adds
  "Metadata: read". No organisation or account permissions;
- install it with "Only select repositories" and select `troupe`, `infrastructure` and `website`, and add its row to
  the table above.

Its installation is checked by `oob.py` against `app-installations.json`. Its client ID isn't secret, and it's
written in the workflow (`client-id`), so a pull request's run can use it before its merge (design D3).

**Its key.** Generate a private key in the App's settings. Store it in 1Password as an SSH Key item named
`troupe-run-review` in vault `troupe.run`, by importing the downloaded `.pem`, then delete the file. It's an org
secret visible to the three repositories only: not in an environment, because the pull request runs that need it
aren't on `main`. Any member's pull request run can reach it, which gives contents read and pull request write on
three public repositories. Nothing is printed:

```sh
export OP_ACCOUNT=l-a-u.1password.com
# gh runs only once op has read the key, and only if it's PKCS#1 or PKCS#8 (create-github-app-token refuses OpenSSH).
key=$(op read -n "op://troupe.run/troupe-run-review/private key") &&
  case "$key" in "-----BEGIN RSA PRIVATE KEY-----"*|"-----BEGIN PRIVATE KEY-----"*) ;; *) false ;; esac &&
  printf '%s' "$key" | gh secret set REVIEW_APP_PRIVATE_KEY --org troupe-run \
    --visibility selected --repos troupe,infrastructure,website
unset key
```

**The Claude token.** Run `claude setup-token` and sign in as the account the reviews are billed to. It prints a token
that lasts a year (the current one expires about 2027-10-26). Store it in 1Password as an API Credential item named
`troupe-run-claude-review`, field `credential`, in vault `troupe.run`. It's billed to that account's subscription and
shares its usage limits. Set it the same way:

```sh
export OP_ACCOUNT=l-a-u.1password.com
# gh runs only once op has read the token, so a failed read can't set an empty secret.
token=$(op read -n "op://troupe.run/troupe-run-claude-review/credential") &&
  printf '%s' "$token" | gh secret set CLAUDE_CODE_OAUTH_TOKEN --org troupe-run \
    --visibility selected --repos troupe,infrastructure,website
unset token
```

Check each by name, never by value. Each should list exactly `infrastructure`, `troupe` and `website`:

```sh
gh api orgs/troupe-run/actions/secrets/REVIEW_APP_PRIVATE_KEY/repositories --jq '.repositories[].name'
gh api orgs/troupe-run/actions/secrets/CLAUDE_CODE_OAUTH_TOKEN/repositories --jq '.repositories[].name'
```

**Rotating them.** For the key: generate a new one in the App's settings, replace the 1Password item's key, run its
set command, then delete the old key in the App's settings. For the token: before it expires, run `claude setup-token`
again, replace the 1Password item's credential, and run its set command. A missing or expired credential fails only
the review, which isn't a required check.

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
are Cloudflare's defaults, except Universal SSL, which `tofu/dns.json` declares off: nothing is proxied, so they don't
touch the site. With Universal SSL on, Cloudflare adds CAA records for its own CAs beside the declared ones, which
aren't in the dashboard or the API, so the plan can't report them. Off, the declared records are the whole policy;
check with `dig CAA troupe.run @audrey.ns.cloudflare.com` (spec: dns).

**The token.** A custom account API token with Zone → DNS → Edit, Zone → SSL and Certificates → Edit and Zone → Zone →
Read, on troupe.run only, no IP filter and no expiry. SSL and Certificates is there so a plan can read the Universal
SSL setting and an apply can change it; it also lets the token manage this zone's edge certificates, but not its SSL
mode or TLS versions (Zone Settings), and nothing beyond the zone (declare-universal-ssl design D3). It's in
1Password as `troupe-run-cloudflare-dns`, field `credential`, in vault `troupe.run`, and in CI's three environments as
`TF_VAR_cloudflare_api_token` (README). Check its scope without printing it:

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
