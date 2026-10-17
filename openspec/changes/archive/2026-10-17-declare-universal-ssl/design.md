# Design: declare troupe.run's Universal SSL setting with its CAA records

## Context

See proposal.md for why. What shapes the approach:

- **What troupe.run publishes (`dig CAA troupe.run @audrey.ns.cloudflare.com`, 2026-10-17):** `issue` for
  `comodoca.com`, `digicert.com; cansignhttpexchanges=yes`, `letsencrypt.org`, `pki.goog; cansignhttpexchanges=yes`
  and `ssl.com`; `issuewild` for `;` and the same five. Only `issue letsencrypt.org` and `issuewild ;` are ours. The
  API's record list, which the undeclared-records check reads, has only those two, so the check is silent.
- **Cloudflare's docs** say the records are added "when you have Universal SSL and add any CAA records to your
  zone", and "will not appear in the Cloudflare dashboard". They don't say whether turning Universal SSL off removes
  them.
- **Provider:** `cloudflare/cloudflare` 5.28. `cloudflare_universal_ssl_setting` takes `zone_id` and `enabled`, needs
  SSL and Certificates Read (to plan) and Write (to apply), and imports by `<zone_id>`. Its `Delete` is empty in
  v5.28.0: removing the resource only forgets it, and the zone keeps whatever setting it has.
- **The token** has Zone → DNS → Edit and Zone → Zone → Read on troupe.run. Universal SSL was read with it during
  manage-dns-as-code (its task 1.2) and refused with a 403, so a plan with this resource fails until the token gains
  SSL and Certificates.
- **manage-dns-as-code** made "managing the Cloudflare zone or its settings" a non-goal (its design D2), because the
  settings are defaults and nothing is proxied. This change takes on one setting, because it decides what a declared
  record means. The zone itself stays read, not managed.
- **Precedents:** declarations are JSON with a pytest module in `scripts/check.py` (`test_dns.py`), live objects are
  adopted by `import` blocks in `tofu/imports.tf` with literal IDs, and what's set up by hand is in `oob/README.md`.

## Goals / Non-Goals

**Goals:**
- One place says whether Universal SSL is on, beside the CAA records, and the plan shows any difference from it.
- The spec's CAA requirement is true of what the nameservers answer, and says how to check it.
- Adopting the setting changes nothing in the zone.

**Non-Goals:**
- Turning Universal SSL off, or finding out what that does to the added records (proposal, out of scope).
- Managing any other zone setting. A setting that changes what a declared record means joins `dns.json` the same way,
  by its own change.
- Checking published CAA answers in the plan. That needs a DNS query from the plan, a new provider for one check, and
  the answer depends on Cloudflare's CA list, which isn't ours.

## Decisions

### D1. `universal_ssl` is a required top-level boolean in `tofu/dns.json`

`dns.json` already says what troupe.run publishes, and this setting changes what its CAA records mean, so it goes
there: `"universal_ssl": true`, beside `zone` and `ttl`. `test_dns.py` adds it to the required top-level fields, and
refuses any value that isn't `true` or `false`, naming the field and what it takes. A string such as `"false"` is
refused, not read as truthy (a malformed input is an error).

Alternatives: `enabled = true` written in `dns.tf`, which puts the decision in a different file from the records it
qualifies, so a CAA edit could be reviewed without it in view; a `settings` object in `dns.json`, which is structure
for one value. If a second setting arrives, grouping can come then.

The declared CAA records don't change: `issuewild ";"` is what applies whenever Universal SSL is off, and is harmless
while it's on.

### D2. The setting is imported by the zone's ID

`dns.tf` adds `cloudflare_universal_ssl_setting.troupe_run`, with `zone_id` from `data.cloudflare_zone.troupe_run`
and `enabled = local.dns.universal_ssl`. `tofu/imports.tf` imports it with
`id = "f716f063a26f15bcfcecd62791cdd202"`, the zone's ID, written out like the records' import IDs. The first plan
must show one import and no change: if it shows `enabled` changing, the zone isn't as observed and the change stops.

No `prevent_destroy`: the provider's `Delete` does nothing, so removing the block can't change the zone, only stop
managing it. That's said in a comment, so nobody adds a guard against a destroy that can't happen.

### D3. The owner adds SSL and Certificates → Edit to the existing token

Editing the token in place keeps its value, so the 1Password item `troupe-run-cloudflare-dns` and the three CI
environments' `TF_VAR_cloudflare_api_token` don't change. The scope stays troupe.run only. What it adds: the token can
read and change this zone's Universal SSL setting and its edge certificates, which the provider's documented
permission for this resource requires. The zone's SSL mode and TLS versions are Zone Settings, a separate permission
the token doesn't have: with it, `/settings/ssl` was still refused (task 1.2). A separate token for SSL would mean a second secret
in every environment and in `scripts/tofu.py`, for the same zone and the same plan.

It must happen before the pull request's first plan: without it, the plan's read of the setting is refused. It's
verified through `op run`, without printing the token: the Universal SSL settings endpoint answers 200, where it was
403, and the zone list is still only `troupe.run`.

### D4. The drift scenario is shown by a plan, not by changing the live zone

The setting is the zone's real one, and there's one zone. Turning Universal SSL off by hand to show drift would
remove the edge certificate and might change the CAA answers in a way nobody has tested. Instead, a local plan with
`universal_ssl` set to `false` in the working tree (never committed or applied) must show `enabled` changing from
`true` to `false`; with it set back, the plan is clean. That proves the plan reads the zone's value and compares it
with the declaration, which is the whole drift mechanism, in the direction that's safe to plan.

### D5. Published CAA answers are checked with `dig`, and the spec says why

The API doesn't list Cloudflare's added records, so the undeclared-records check can't see them, and no OpenTofu
check can without querying DNS (Non-Goals). The spec says so, and the scenarios with Universal SSL on are checked by
querying the zone's nameservers and comparing every name with Cloudflare's CAA documentation. The CA list is the docs',
not ours, so the spec names the docs rather than copying the four names, which would go stale when Cloudflare changes
CAs.

### D6. The test that claimed Let's Encrypt only is renamed

`test_only_lets_encrypt_may_issue` checks the declared CAA records, not what's published, and with Universal SSL on
its name is false. It becomes `test_the_declared_caa_records_name_only_lets_encrypt`, with the same body.

## Risks / Trade-offs

- [The token can now change Universal SSL and the zone's edge certificates, which would affect the site once anything is proxied] → It's scoped to
  troupe.run, held in 1Password and CI's environments only, and every change it makes through this repo is a planned,
  approved apply. Nothing is proxied, so today those settings don't touch what visitors get.
- [Cloudflare changes which CAs it adds] → The spec names Cloudflare's docs, not the list, and the `dig` check
  compares against the docs at the time.
- [Someone turns Universal SSL off assuming the CAA answers then match the declaration] → The spec's "off" scenario
  is the claim to check; `oob/README.md` says it hasn't been tested and to try it on the probe first.

## Migration Plan

1. The owner edits the token (D3), verified through `op run`.
2. The pull request adds the declaration, resource, import and tests; its plan shows one import and no change.
3. After the owner approves the apply, the next plan is clean, and `dig` shows the same answers as before.

Rollback: removing the resource and the import changes nothing in the zone (D2). Removing the token's new permission
afterwards makes any plan with the resource fail to read it, so do it only once the resource is gone.
