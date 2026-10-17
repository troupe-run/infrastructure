## REMOVED Requirements

### Requirement: CAA limits who may issue certificates
**Reason**: It allowed Universal SSL to be on, which lets Cloudflare add CAA records for its own CAs. The owner's
intent is Let's Encrypt only, with Universal SSL off (2026-10-17, #81).
**Migration**: Replaced by "Only Let's Encrypt may issue certificates", which keeps the published-record and Pages
scenarios and drops the ones for Universal SSL on.

## ADDED Requirements

### Requirement: Only Let's Encrypt may issue certificates
troupe.run SHALL publish CAA records that let only Let's Encrypt issue certificates for it, and forbid wildcards.
Universal SSL SHALL be off for the zone: while it's on, Cloudflare adds CAA records for its own CAs that the API
doesn't list. GitHub Pages SHALL still issue the site's certificate. A CNAME, such as `www`, takes its target's CAA
policy.

#### Scenario: Only the declared CAA records are published
- **WHEN** CAA for `troupe.run` is queried at the zone's nameservers
- **THEN** `issue` names only `letsencrypt.org`, and `issuewild` is only `;`

#### Scenario: Universal SSL is declared off
- **WHEN** `scripts/check.py` runs on a declaration with `universal_ssl` on
- **THEN** it fails, naming `universal_ssl` and why it must be off

#### Scenario: Pages still issues a certificate
- **WHEN** GitHub Pages is made to issue a new certificate for troupe.run with the CAA record published
- **THEN** a new certificate from Let's Encrypt is issued, and https://troupe.run serves it
