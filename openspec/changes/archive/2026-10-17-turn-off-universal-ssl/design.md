# Design: turn troupe.run's Universal SSL off

## Context

See proposal.md for why. What shapes the approach:

- **Today (2026-10-17, after #79's apply):** `universal_ssl` is `true` in `tofu/dns.json`, and
  `cloudflare_universal_ssl_setting.troupe_run` manages it. Both of Cloudflare's nameservers answer CAA with our
  `issue letsencrypt.org` and `issuewild ;`, plus `issue` and `issuewild` for `comodoca.com`, `digicert.com`,
  `pki.goog` and `ssl.com`, and `issuewild letsencrypt.org`.
- **Cloudflare's docs** say turning Universal SSL off removes its edge certificates and stops new ones being ordered,
  and that HSTS, Always Use HTTPS and HTTPS redirects then break for proxied traffic. They don't say whether the CAA
  records it added go too.
- **Nothing is proxied** (spec dns). Visitors reach GitHub Pages directly and get its Let's Encrypt certificate, so
  the edge certificate is unused.
- **The probe can't isolate this.** It works under `infra-probe.troupe.run` in the same zone, and the token reaches no
  other zone, so turning Universal SSL off on the probe is turning it off on troupe.run. The test is the change itself.
- **The plan after #79's apply wasn't confirmed clean** (the local plan's 1Password prompt timed out). This change's
  plan is the first since that apply.

## Goals / Non-Goals

**Goals:**
- Universal SSL off, through the plan-and-approve path, and troupe.run's CAA answer exactly what's declared.
- Turning it back on needs a spec change, not a one-word edit to `dns.json`.

**Non-Goals:**
- Anything that would need an edge certificate, such as proxying.
- Removing `cloudflare_universal_ssl_setting` or the token's SSL permission. Declaring the setting is what keeps it
  off: without it, a dashboard change would go unreported.

## Decisions

### D1. Off is declared, applied by CI, and checked by the plan

`"universal_ssl": false`. The pull request's plan must show exactly one change, `enabled = true -> false`. Anything
else is drift left over from #79's apply, and is looked at before going on. The owner approves the apply as usual.

### D2. The check refuses `universal_ssl: true`

`declaration_problems` in `test_dns.py` gains: when `universal_ssl` is `true`, the problem names it and says why it
must be off (Cloudflare adds CAA records for its own CAs, spec dns). The live declaration is checked by the existing
`test_the_declaration_is_well_formed`. The generic test helper's default becomes `false`, and
`test_universal_ssl_takes_true_and_false` becomes two tests: one that `false` is accepted, one that `true` is refused
with that message.

Alternative: a separate test that only reads the live file. That would leave `declaration_problems` accepting a
declaration the spec forbids, so the error message `check.py` prints wouldn't say what's wrong.

### D3. The CAA answer is checked after the apply, and the change isn't done until it's exact

After the apply, query CAA at both nameservers. The `dig` goes to the authoritative servers, so caching doesn't
delay it, but Cloudflare may take time to update. Check again over about an hour. The change is archived before the merge, as
every change is, so the result is recorded on #81. If Cloudflare's records are still there after that, #81 is
reopened and the owner gets the findings with options (re-saving the CAA records through a planned replace, or asking
Cloudflare), for a follow-up change. That isn't designed in advance, because Cloudflare doesn't document what removes
them.

### D4. Docs say it's off and why

`oob/README.md`'s zone paragraph says Universal SSL is declared off so the CAA records are the whole policy, and the
"untested" note is replaced by what the apply showed. `dns.tf`'s comment and README.md's row say the same. The token's
paragraph keeps SSL and Certificates → Edit, which planning the setting still needs, and its over-long line is
rewrapped.

## Risks / Trade-offs

- [Cloudflare's CAA records stay after Universal SSL is off] → D3: checked after the apply; if they stay, #81 is
  reopened for a follow-up.
- [Proxying is wanted later] → It would need an edge certificate, and so Universal SSL on or an advanced certificate.
  That's a spec change with its own decision.
- [Turning it back on] → Set `universal_ssl` back to `true` and change the spec. Cloudflare orders a new edge
  certificate; the site isn't affected either way, because nothing is proxied.

## Migration Plan

1. The pull request: declaration, check, docs. Its plan shows one update.
2. The owner merges by rebase and approves the apply.
3. `dig` at both nameservers (D3), then https://troupe.run is checked.

Rollback: `"universal_ssl": true`, with the check and spec changed back, through the same path.
