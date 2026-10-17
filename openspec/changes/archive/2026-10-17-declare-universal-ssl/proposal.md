# Declare troupe.run's Universal SSL setting with its CAA records

## Why

troupe.run's CAA policy isn't what the `dns` spec says it is. #55 published `0 issue "letsencrypt.org"` and
`0 issuewild ";"`, but Cloudflare adds CAA records for its own certificate authorities whenever Universal SSL is on and
the zone has any CAA record, and those records don't appear in the dashboard or the API
([Cloudflare docs](https://developers.cloudflare.com/ssl/edge-certificates/caa-records/)). On 2026-10-17 the apex
answered with ours plus `issue` and `issuewild` for `comodoca.com`, `digicert.com`, `pki.goog` and `ssl.com`, and
`issuewild` for `letsencrypt.org` too. So "Only Let's Encrypt may issue certificates" doesn't hold, and the
`issuewild ";"` that was meant to forbid wildcards is overridden.

The owner keeps Universal SSL on (2026-10-17, #75): proxying troupe.run through Cloudflare later, for caching or DDoS
protection, needs an edge certificate, and issuance is still limited to five CAs rather than any. The setting decides
which CAA policy is real, so it belongs next to the records, in one place, changed only by a pull request and an
approved plan, rather than in the dashboard.

## What Changes

- **The token** gains Zone → SSL and Certificates → Edit on troupe.run. The owner edits it in place, so its value, the
  1Password item and CI's environment secrets don't change. It can then also manage this zone's edge certificates,
  but not its SSL mode or TLS versions, and nothing beyond the zone.
- **`tofu/dns.json`** gains a top-level `universal_ssl` (`true`). `scripts/tests/test_dns.py` refuses a declaration
  without it, or with a value that isn't a boolean.
- **`tofu/dns.tf`** manages `cloudflare_universal_ssl_setting` for the zone from that value. It's adopted with an
  `import` block, and the first plan imports it with no change.
- **The `dns` spec** says what troupe.run actually publishes: with Universal SSL on, issuance is limited to Let's
  Encrypt and the CAs Cloudflare adds, for wildcards too; with it off, to Let's Encrypt only, with no wildcards.
  Cloudflare's added records aren't in the API, so the plan's undeclared-records check can't see them; the spec says
  so, and the CAA scenario is checked with `dig` against the zone's nameservers.
- **`oob/README.md`** records the token's new scope, and drops the advice to turn Universal SSL off by hand.

Out of scope: proxying any record (it changes how GitHub Pages renews its certificate, and needs an SSL mode
decision), and turning Universal SSL off. Cloudflare's docs don't say whether turning it off removes the records it
added, so that's tested on the probe first if the owner ever wants it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dns`: the CAA requirement is restated as what's published with Universal SSL on or off; a new requirement declares
  the Universal SSL setting once and shows a change made by hand as drift; a declaration without `universal_ssl` is
  refused.

## Impact

- `tofu/dns.json`, `tofu/dns.tf`, `tofu/imports.tf` (one `import` block), `scripts/tests/test_dns.py`,
  `oob/README.md`, and the README's row for the DNS files.
- The Cloudflare API token's permissions (owner, by hand). No new secret, variable or provider.
- No change to anything troupe.run serves: the setting is imported as it is (`enabled = true`), and no record changes.
