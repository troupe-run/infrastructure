# Proposal: manage troupe.run's DNS as code

## Why

https://troupe.run depends on DNS records nobody declares. They were set by hand and nothing checks them: four A and
four AAAA records for GitHub Pages, `www` as a CNAME to `troupe-run.github.io.`, and the TXT record that verifies
troupe.run for the org (#55). The domain also publishes nothing that stops someone sending mail as it or limits who
may issue its certificates.

The owner chose the tool on 2026-10-17 (#55): Cloudflare hosts the DNS, managed with OpenTofu in the same root as
everything else. Gandi's OpenTofu provider has had no release since 2024-01-09. DNSControl's Gandi backend is
community-supported, so it carries the same "not supported" risk, and it would be a second tool needing its own
plan-and-approve gate in CI. Cloudflare keeps one tool and one approval path.

The move itself is done. On 2026-10-17 the owner added troupe.run to Cloudflare and switched its nameservers at
Gandi. Cloudflare's scan copied every record in Gandi's zone, unproxied, and it serves them now. What's left is
bringing those records under management, and adding the new ones.

## What Changes

- **Cloudflare's records are adopted as they are.** The records Cloudflare serves are imported, and the first plan
  shows them imported with no change: A 185.199.108–111.153, AAAA 2606:50c0:8000–8003::153, `www` CNAME
  `troupe-run.github.io.`, and `_gh-troupe-run-o` TXT (the org's domain verification). TTL stays at Cloudflare's
  automatic value. They match Gandi's zone export record for record (owner, 2026-10-17).
- `tofu/dns.json` declares every record once, and `tofu/dns.tf` manages them in the Cloudflare zone with the
  `cloudflare/cloudflare` provider. No record is proxied by Cloudflare: GitHub Pages issues and serves the
  certificate, and a proxied record would break that.
- **New records** (owner, 2026-10-17):
  - The domain sends no mail: a null MX (`0 .`), SPF `v=spf1 -all`, and a DMARC record with `p=reject`.
  - A CAA record lets only Let's Encrypt issue certificates, since GitHub Pages issues with it today (the live
    certificate is from Let's Encrypt `YR1`). It's tested live, because troupe.run has no traffic yet: Pages is made
    to issue a new certificate after the record is published.
  - GitHub's Pages domain verification for the org (`_github-pages-challenge-troupe-run`). troupe.run wasn't a Pages
    verified domain. It's verified for the org, which is a different check. Verifying it for Pages stops another
    account's Pages site from claiming the domain. The owner started it and added its record in Cloudflare by hand on
    2026-10-17, so the record is adopted with the others rather than created.
- The Cloudflare API token is a new secret. It can only edit DNS in the troupe.run zone. It comes from 1Password at
  run time like the others, is an ephemeral variable so no saved plan holds it, and is set in all three CI
  environments by the owner.
- `scripts/check.py` refuses a malformed declaration: a duplicate key, an unknown record type, or a field missing or
  not allowed for its type.
- A plan reports a record in the zone that isn't declared, and a zone that Cloudflare doesn't consider active (for
  example, because the nameservers at Gandi changed).
- What's set up by hand (the Cloudflare account and zone, the token, and the nameservers at Gandi) is recorded in
  `oob/README.md`, with the rollback.

Out of scope:

- **DNSSEC.** Cloudflare offers it, but enabling it means a DS record at Gandi. It deserves its own issue once the
  move has settled.
- **Moving the registration** away from Gandi.
- **Deleting the old records at Gandi's LiveDNS.** They stay as they are, so switching the nameservers back is the
  rollback. Clearing them later is a separate decision.
- **Cloudflare zone settings** beyond what the records need, such as the SSL mode. Nothing is proxied, so they don't
  affect the site. They're recorded in `oob/README.md` as left at their defaults, apart from any the CAA record needs
  (design D7).

## Capabilities

### New Capabilities

- `dns`: troupe.run's DNS records, declared once and served by Cloudflare. Covers which records exist and how the live
  ones were adopted, that none is proxied, the mail lockdown, the CAA policy, the org's and Pages' domain verification
  records, the declaration's validation, and how an undeclared record or an inactive zone shows up.

### Modified Capabilities

- `state-and-apply`: "Secrets are supplied at run time" and "A saved plan holds no key" name the App key and the
  state passphrase. Both now cover the Cloudflare token too.
- `ci-apply`: "A pull request's run holds no credential without the owner's approval" lists the credentials a run
  gets. It gains the Cloudflare token.

## Impact

- New: `tofu/dns.json` and `tofu/dns.tf`, and eleven `import` blocks in `tofu/imports.tf`. `tofu/versions.tf` adds the
  `cloudflare/cloudflare` provider, `tofu/providers.tf` its configuration and the ephemeral token variable, and
  `tofu/.terraform.lock.hcl` its hashes for every platform the lock file already covers.
- `tofu/secrets.env`, `scripts/tofu.py` (`SECRETS`), `.github/workflows/tofu.yml` (each job's `env`) and the README's
  secrets section gain `TF_VAR_cloudflare_api_token`.
- `scripts/check.py`'s tests gain the declaration's validation. `tofu/probe/` gains a DNS section. `oob/README.md`
  gains the Cloudflare section.
- Set up by the owner, by hand: the scoped API token, in 1Password and in the three CI environments; starting Pages
  domain verification, and completing it once the record is served.
- The live site: the import changes nothing served. The apply adds the mail, CAA and Pages verification records, and
  those are the only changes to troupe.run's answers.
