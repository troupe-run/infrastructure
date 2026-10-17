# Turn troupe.run's Universal SSL off

## Why

The aim of #75 was control over which CA may issue certificates for troupe.run, so the Let's Encrypt certificate GitHub
Pages gets is the only kind there is, with the setting managed here. #75 brought Cloudflare's Universal SSL setting
into `tofu/dns.json`, but recorded it as on, which wasn't the owner's intent (owner, 2026-10-17, #81). While it's on,
Cloudflare publishes CAA records for its own CAs beside ours (`comodoca.com`, `digicert.com`, `pki.goog`, `ssl.com`,
and `issuewild letsencrypt.org`), which the API doesn't list. Which CAs those are doesn't matter; that they're there
does.

## What Changes

- **`tofu/dns.json`**: `"universal_ssl": false`. The apply turns Universal SSL off for the zone. Nothing is proxied, so
  the site keeps GitHub's certificate; the Universal SSL edge certificate Cloudflare holds, which nothing serves, is
  removed.
- **`scripts/tests/test_dns.py`** checks the declaration has it off, so turning it back on is a spec change, not a
  one-word edit.
- **The `dns` spec**: Universal SSL is off, so troupe.run's CAA answer is exactly the declared records: Let's Encrypt
  only, no wildcards. The scenarios for "on" go.
- **After the apply**, the CAA answer at both of Cloudflare's nameservers is checked. Cloudflare's docs don't say
  whether turning Universal SSL off removes the records it added; if they stay, this change isn't done until they're
  gone.
- **`oob/README.md`**, **`tofu/dns.tf`**'s comment and **README.md**'s row say it's off, and why.

Out of scope: proxying any record. It would need an edge certificate again, and an SSL mode decision.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dns`: "CAA limits who may issue certificates" is replaced by "Only Let's Encrypt may issue certificates", which
  requires Universal SSL off, so the declared CAA records are the whole policy. Its scenarios for Universal SSL on go.

## Impact

- `tofu/dns.json`, `tofu/dns.tf` (comment), `scripts/tests/test_dns.py`, `oob/README.md`, README.md.
- One live change: the zone's Universal SSL goes from on to off. Reversible by setting it back to `true` (Cloudflare
  orders a new edge certificate). No token, secret or provider change.
